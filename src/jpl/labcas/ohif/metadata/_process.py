# encoding: utf-8

'''🔬 OHIF LabCAS metadata loader processes DICOM files, extracts metadata, and loads it into Solr.'''


import logging, pysolr, os, subprocess, tempfile, os.path, json, glob

_logger = logging.getLogger(__name__)

# These keys we strip out because they're problematic:
#
# - `PatientName` I've see a single valued string containing a dict with a single key `Alphabetic`
#    whose value is a string — what even is that? 😐
# - `ROIContourSequence` its value is a massive 1.7 million characters long
# - `StructureSetROISequence` value is a nested JSON structure so strip it
# - `ReferencedFrameOfReferenceSequence` vlaue is 13160 characters long

_forbidden_keys = set([
    'PatientName',
    'ROIContourSequence',
    'StructureSetROISequence',
    'ReferencedFrameOfReferenceSequence',
    'ConceptNameCodeSequence',
    'ReferencedSeriesSequence',
])


def _find_dcm_dirs(top: str):
    '''Generate any folders that contain at least one file ending in `.dcm` regardless of case.'''
    for root, _, files in os.walk(top):
        if any(f.lower().endswith('.dcm') for f in files):
            yield root


def _find_rs_dirs(top: str):
    '''Generate any folders that contain at least one file matching `RS*.dcm` regardless of case.'''
    for root, _, files in os.walk(top):
        if any(f.startswith('RS') and f.lower().endswith('.dcm') for f in files):
            yield root


def _add_all_except(skip_key: str, from_dict: dict, to_dict: dict):
    '''Add all keys `from_dict` `to_dict` except the `skip_key`.'''
    to_dict.update({k: v for k, v in from_dict.items() if k != skip_key})


def _collapse(folder: str, metadata: dict) -> tuple:
    '''"Collapse" the `metadata` and return an altered version of it.

    This is based on @yuliujpl's description in https://github.com/jpl-labcas/publish/issues/22

    This returns a tuple of the collapsed metadata plus a list of found URLs.
    '''
    if 'studies' not in metadata:
        # The top-level key should always be `studies`. If it's not there, forget it
        _logger.info('😵‍💫 For folder %s there was not a top level `studies` key in the metadata', folder)
        return {}, []

    collapsed, studies, urls = {}, metadata['studies'], []
    for study in studies:
        _add_all_except('series', from_dict=study, to_dict=collapsed)
        for episode in study['series']:
            _add_all_except('instances', from_dict=episode, to_dict=collapsed)
            for instance in episode['instances']:
                # Once we get to instances, there are only two keys, `metadata` and `url`, and
                # we add all of the `metadata`'s dict values to the `collapsed`.
                collapsed.update(instance['metadata'])
                urls.append(instance['url'])
    return collapsed, urls


def _generate_metadata(folder: str, prefix: str, dicomjs: str) -> tuple:
    '''Return a dict of the metadata that should be applied to files in `folder`.

    Note that the `dicom-json-generator.js` is pretty sub-par:

    - The only non-zero exit status is for incorrect command-line arguments.
    - If it has a file it can't read (such as a bad symlink), it aborts and makes no output file.
    - If it any file is a bad DICOM file (bad header, for example), it aborts and makes no output file.

    Even if other files could produce data, one file poisons the batch.

    So we have to look for the output file's nonexistence.

    This returns a tuple of metadata (dict) and URLs (list).
    '''
    _logger.info('🧠 Generating metadata for folder %s', folder)
    name = None
    try:
        tf = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tf.close()
        name = tf.name
        args = ['node', dicomjs, folder, prefix, name]
        cp = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, check=True)
        if os.path.getsize(name) == 0:
            _logger.error(
                '💣 The DICOM generator failed on %s; stdout=%s, stderr=%s; continuing on',
                folder, cp.stdout, cp.stderr
            )
            return {}, []
        with open(name, 'r') as io:
            return _collapse(folder, json.load(io))
    except subprocess.CalledProcessError:
        _logger.exception('💣 The DICOM generator aborted on folder %s', folder)
        return {}, []
    except json.JSONDecodeError:
        _logger.exception('💣 The DICOM generator produced bad JSON working on folder %s', folder)
        return {}, []
    finally:
        if name is not None:
            os.unlink(name)


def _apply_metadata_updates(solr: pysolr.Solr, metadata: dict, urls: list):
    _logger.info('💄 Applying metadata updates to files in %r', urls)
    for url in urls:
        # We need to search Solr for the `name` field so let's strip off the last item
        #
        # FileName has the "virtual" file name with the event ID, which we can't use
        fn = url.split('/')[-1]
        updates = metadata.copy()
        updates['url'] = url

        _logger.debug('🔎 Searching Solr for name %s', fn)
        # The "AND NOT url:*" enables us to only do the ones that need the additional metadata,
        # skipping those that already have it.
        for doc in solr.search(f'name:{fn} AND NOT url:*', rows=1):
            payload = {
                'id': doc['id'],
                **{k: {'set': v} for k, v in updates.items()}
            }
            try:
                solr.add([payload], commit=True)
                break  # Only update first doc; you'd think rows=1 would do it but defensive
            except Exception as ex:
                _logger.exception('🌞 Solr failure %s adding «%s»', str(ex), [payload])


def _clean_metadata(metadata: dict) -> dict:
    '''Clean up the `metadata` for LabCAS.

    In particular:

    - Remove any keys whose values are empty strings (I've seen `AccessionNumber`)
    - Turn any keys whose values are strings into lists of single strings (like most of them)
    - Leave any lists of multiple values intact (like `ImageType`)
    '''
    cleaned = {}
    for k, v in metadata.items():
        if v == '': continue
        if k in _forbidden_keys: continue
        if isinstance(v, str):
            cleaned[k] = [v]
        elif isinstance(v, int):
            cleaned[k] = [str(v)]
        else:
            cleaned[k] = v
    return cleaned


def process(solr: pysolr.Solr, folder: str, prefix: str, dicomjs: str):
    '''Process using `solr` on `folder` with `prefix` and the `dicomjs`.

    This generates additional metadata for DICOM files and fills `solr` with it.
    '''
    _logger.info('🏁 Beginning processing of %s with prefix %s using Solr %r', folder, prefix, solr)

    for f in _find_dcm_dirs(folder):
        _logger.debug('Found a folder with .dcm files: %s', f)
        metadata, urls = _generate_metadata(f, prefix, dicomjs)
        metadata = _clean_metadata(metadata)
        _apply_metadata_updates(solr, metadata, urls)


def _locate_rs_file(folder: str) -> str:
    '''The `folder` contains an `RS*.dcm` file so give its exact name.'''
    pattern = os.path.join(folder, 'RS*.dcm')
    matches = glob.glob(pattern)
    if not matches: return None
    return os.path.basename(matches[0])


def _apply_metadata_to_rs_file(solr: pysolr.Solr, metadata: dict, rs_file: str):
    '''Look up `rs_file` in Solr and write the `metadata` as a JSON serialized string into `solr`.

    We are to use the Solr field `ohif_dcm_json`. The `solr` is for the `files` core already.
    '''
    serialized = json.dumps(metadata)
    _logger.info('Adding `ohif_dcm_json` field (with %d characters) to Solr file %s', len(serialized), rs_file)
    updated = False
    for doc in solr.search(f'name:{rs_file}', rows=1):
        payload = {'id': doc['id'], 'ohif_dcm_json': {'set': serialized}}
        try:
            solr.add([payload], commit=True)
            updated = True
            break  # Only update first doc; you'd think rows=1 would do it but doing some defensive dev
        except Exception as ex:
            _logger.exception('🌞 Solr failure %s writing ohif_dcm_json payload «%s»', str(ex), [payload])
    if not updated:
        _logger.info('No matches for name:%s in Solr, so moving on', rs_file)


def postprocess(solr: pysolr.Solr, folder: str, prefix: str, dicomjs: str):
    '''Postprocess using `solr` on `folder` with `prefix` and the `dicomjs`.

    This generates huge JSON dictionaries and puts them into specific files in Solr.
    '''
    _logger.info('🏁 Beginning postprocessing of %s with prefix %s using Solr %r', folder, prefix, solr)

    for f in _find_rs_dirs(folder):
        _logger.debug('Found a folder with an RS*.dcm file in it: %s', f)
        metadata, _ = _generate_metadata(f, prefix, dicomjs)
        metadata = _clean_metadata(metadata)
        rs_file = _locate_rs_file(f)
        if not rs_file:
            _logger.warning('The RS*.dcm file disappeared from %s; moving on', f)
            continue
        _apply_metadata_to_rs_file(solr, metadata, rs_file)
