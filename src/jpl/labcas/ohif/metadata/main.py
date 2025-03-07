# encoding: utf-8

'''🔬 OHIF LabCAS metadata loader processes DICOM files, extracts metadata, and loads it into Solr.'''


from ._argparse import add_standard_argparse_options
from ._process import process
from .const import GENERATOR_JS, DEFAULT_STRIP_PREFIX, DEFAULT_SOLR_URL
import argparse, logging, pysolr, sys, os.path, subprocess

_logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_standard_argparse_options(parser)
    parser.add_argument('-s', '--solr', metavar='URL', default=DEFAULT_SOLR_URL, help='Solr URL (default %(default)s)')
    parser.add_argument(
        '-g', '--generator',
        help=f'Path to the {GENERATOR_JS} file; defaults to finding it in the current directory'
    )
    parser.add_argument(
        '-p', '--prefix', default=DEFAULT_STRIP_PREFIX,
        help='Path prefix to strip for URL generation; defaults to %(default)s'
    )
    parser.add_argument('folder', help='Folder in which to search for .dcm files')
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel, format='%(levelname)s %(message)s')

    # Setup and check Solr
    solr_url = args.solr if args.solr.endswith('/') else args.solr + '/'
    solr = pysolr.Solr(solr_url + 'files', always_commit=True, verify=False)
    solr.ping()

    # Sanity check on the generator
    generator = os.path.abspath(args.generator) if args.generator else os.path.abspath(os.path.join('.', GENERATOR_JS))
    if not os.path.isfile(generator):
        logging.error("❌ Expected a DICOM JSON Generator at %s but it's not found", generator)
        sys.exit(-1)

    # Check the .dcm folder
    folder = args.folder if not args.folder.endswith('/') else args.folder[:-1]
    if not os.path.isdir(folder):
        logging.error("❌ Expected a folder at %s but it's not", folder)

    # Check Node and the required installation module
    subprocess.run(
        ['node', '--version'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=True
    )
    subprocess.run(
        ['node', '--eval', "require('dcmjs');"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, check=True
    )

    # Check the prefix
    prefix = args.prefix if args.prefix.endswith('/') else args.prefix + '/'

    # Ready to go!
    process(solr, folder, prefix, generator)
    sys.exit(0)


if __name__ == '__main__':
    main()
