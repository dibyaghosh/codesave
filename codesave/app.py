import argparse
from .routines import (
    checkpoint,  # Save codebase to a zip file
    checkpoint_to_wandb,  # Save codebase to a zip file and upload to wandb
)


# These are routines to download codebase from wandb
from .routines import (
    zip_from_wandb
)

from .base import change_launcher # make a zip file runnable

import logging
from pathlib import Path
import shutil

def codesave_app(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "codebase",
        type=str,
        help="A directory to save as a codebase",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Output zip file name", required=True
    )
    parser.add_argument(
        "--extra_libraries",
        type=str,
        default=list(),
        nargs="+",
        help="Extra libraries to include in the codebase",
    )
    parser.add_argument(
        "--extra_pythonpath",
        type=str,
        default=list(),
        nargs="+",
        help="These directories will be scanned for libraries to include in the codebase",
    )
    parser.add_argument("--py_only", action="store_true", help="Only save python files")
    parser.add_argument(
        "--ignore_larger_than", type=str, help="Only save files smaller than this size."
    )

    args = parser.parse_args(args)
    checkpoint(
        main_folder=args.codebase,
        output_zipname=args.output,
        extra_libraries=args.extra_libraries,
        extra_pythonpath=args.extra_pythonpath,
        py_only=args.py_only,
        ignore_larger_than=args.ignore_larger_than,
    )

def wandb_app(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("wandb_path", type=str, help="Wandb path to download")    
    parser.add_argument(
        "-o", "--output", type=str, help="Output zip file name", required=True
    )
    args = parser.parse_args()
    zip_from_wandb(wandb_path=args.wandb_path, output_zipname=args.output)


def make_pyz_app(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "codebase",
        type=str,
        help="Either a already existing zip file, or a directory to first codesave",
    )
    parser.add_argument(
        "launcher",
        type=str,
        help="File or module to run"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="If None, will save to {codebase.stem}.pyz",
    )

    # Only relevant if you pass in a directory into the codebase
    parser.add_argument(
        "--extra_libraries",
        type=str,
        default=list(),
        nargs="+",
        help="Extra libraries to include in the codebase",
    )
    parser.add_argument(
        "--extra_pythonpath",
        type=str,
        default=list(),
        nargs="+",
        help="These directories will be scanned for libraries to include in the codebase",
    )
    parser.add_argument("--py_only", action="store_true", help="Only save python files")
    parser.add_argument(
        "--ignore_larger_than", type=str, help="Only save files smaller than this size."
    )

    args = parser.parse_args(args)

    logging.basicConfig(level=logging.INFO)
    if Path(args.codebase).is_dir():
        logging.info("First creating a codebase")
        if args.output is not None:
            output_zipname = args.output
        else:
            output_zipname = (Path(args.codebase).stem or "codesave") + ".pyz"
        checkpoint(
            main_folder=args.codebase,
            output_zipname=output_zipname,
            extra_libraries=args.extra_libraries,
            extra_pythonpath=args.extra_pythonpath,
            py_only=args.py_only,
            ignore_larger_than=args.ignore_larger_than,
        )
        args.codebase = output_zipname

    
    zip_name = Path(args.codebase)
    if args.output is None:
        args.output = zip_name.parent / (zip_name.stem + ".pyz")
    if Path(args.output) != Path(args.codebase):
        logging.info("Saving to {}".format(args.output))
        shutil.copyfile(args.codebase, args.output)

    external_path, internal_path, module_name = None, None, None
    if Path(args.launcher).is_file():
        external_path = args.launcher
    elif '.py' in args.launcher:
        logging.info(f"Inferring that {args.launcher} is a script inside the zip")
        internal_path = args.launcher
    else:
        logging.info(f"Inferring that {args.launcher} is a module inside the zip")
        module_name = args.launcher
    change_launcher(args.output, external_path=external_path, internal_path=internal_path, module_name=module_name)
