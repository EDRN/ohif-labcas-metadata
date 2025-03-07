# OHIF LabCAS Metadata

This generates metadata for [Open Health Imaging Foundation](https://ohif.org) (OHIF) viewing software for [Digital Imaging and Communications in Medicine](https://www.dicomstandard.org) (DICOM) files and publishes them to the Laboratory Catalog and Archive Service (LabCAS).

## 🧑‍⚕️ Operation

LabCAS is software that catalogs and archives biomedical data for the [Early Detection Research Network](https://edrn-labcas.jpl.nasa.gov/), the (defunct) [Consortium for Molecular and Cellular Characterization of Screen-Detected Lesions](https://mcl-labcas.jpl.nasa.gov/), and the [National Institutes of Standards and Technology](https://labcas.jpl.nasa.gov/nist). The [LabCAS user interface](https://github.com/EDRN/labcas-ui) to communicate with a [backend](https://github.com/jpl-labcas/backend) which in turns takes advantage of [Solr](https://solr.apache.org/) to index and search metadata.

This software updates the metadata directly in Solr.

To generate this metadata, it requires access to the [DICOM JSON Generator](https://raw.githubusercontent.com/OHIF/Viewers/refs/heads/master/.scripts/dicom-json-generator.js). See the requiremets section below for details.


## 📝 Requirements

To use this software, you'll need:

- [Python](https://www.python.org/) version 3.9 or newer, but less than version 4
- [Node.js](https://www.nodejs.org/) version 20 or newer
- Access to LabCAS Solr, usually running on `https://localhost:8984` with a self-signed certificate


## 🏃 Installation and Running

First, ensure you have a relatively new version of Node.js. We require 20 or newer. Try

    node --version

You should see `v2X.Y.Z` where `X = 0` and `Y` and `Z` are any values. Next, add to your Node.js installation the
`dcmjs` API:

    npm install dcmjs

Next, you'll need a copy of a single JavaScript file, namely the one at:

    https://raw.githubusercontent.com/OHIF/Viewers/refs/heads/master/.scripts/dicom-json-generator.js

Save that to a safe location as it is required by this software. We'll call that the "DICOM JSON Generator".

Lastly, install this software. Make a Python virtual environment and use `pip` to install it:

    python3 -m venv DIR
    DIR/bin/pip install ohif-labcas-metadata

You can then run

    DIR/bin/pip/ohif-labcas-loader --help

to see the options.

Replace `DIR` with whatever directory you like.

Note that by default the DICOM JSNO Generator will be found in the current working directory, enabling you to skip `--generator`. Executing `node` will be done with the executable `$PATH`, so make sure that it shows up somewhere there.


### 🚪 Setting the Prefix

The `--prefix` option is used to figure out what parts of each path name we can strip out, and is used in URL generation. By default it's set up for the Early Detection Research Network with the value `/labcas-data/labcas-backend/archive/edrn`, enabling relative URLs to be generated specifically for `edrn-labcas.jpl.nasa.gov`. The stripped value gets passed to the DICOM JSON Generator as its second command line argument.


## 🧑‍🎨 Creators

This software is developed by the Informatics Center at the [Jet Propulsion Laboratory](https://www.jpl.nasa.gov/).

The principal developer is:

- [Sean Kelly](https://github.com/nutjob4life)

The QA team is:

- [David Liu](https://github.com/yuliujpl)


## 👥 Contributing

Within the Informatics Center, we value the health of our community as much as the code. Towards that end, we ask that you read and practice what's described in these documents:

-   Our [contributor's guide](https://github.com/EDRN/.github/blob/main/CONTRIBUTING.md) delineates the kinds of contributions we accept.
-   Our [code of conduct](https://github.com/EDRN/.github/blob/main/CODE_OF_CONDUCT.md) outlines the standards of behavior we practice and expect by everyone who participates with our software.


### 🔢 Versioning

We use the [SemVer](https://semver.org/) philosophy for versioning this software.

## 🪪 License

This software is licensed under the [Apache version 2 license](LICENSE.md).


## 🎨 Art Credits

None at this time.
