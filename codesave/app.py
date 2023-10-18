import argparse
from .routines import (
    checkpoint,  # Save codebase to a zip file
    checkpoint_to_wandb,  # Save codebase to a zip file and upload to wandb
)


# These are routines to download codebase from wandb
from .routines import (
    download_from_wandb,  # download something saved with checkpoint_to_wandb
    zip_from_wandb_artifact,  # download something saved with wandb.run.log_code
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output", type=str, help="Output zip file name", required=True
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--codebase",
        type=str,
        default=None,
        help="If provided, stores this directory as a codebase",
    )
    g.add_argument(
        "--wandb_artifact",
        type=str,
        default=None,
        help="Use if you used wandb.run.log_code",
    )
    g.add_argument(
        "--wandb_path",
        type=str,
        default=None,
        help="Use if you used codesave.checkpoint_to_wandb",
    )

    # Only relevant if you use --codebase
    parser.add_argument(
        "--extra_libraries",
        type=str,
        default=list(),
        nargs="+",
        help="Extra libraries to include in the codebase",
    )
    parser.add_argument("--only_py", action="store_true", help="Only save python files")
    parser.add_argument(
        "--ignore_larger_than", type=str, help="Only save files smaller than this size."
    )

    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    print(args)
    if args.codebase is not None or len(args.extra_libraries) > 0:
        checkpoint(
            main_folder=args.codebase,
            output_zipname=args.output,
            extra_libraries=args.extra_libraries,
            only_py=args.only_py,
            ignore_larger_than=args.ignore_larger_than,
        )
    elif args.wandb_artifact is not None:
        zip_from_wandb_artifact(
            wandb_path=args.wandb_artifact, output_zipname=args.output
        )
    elif args.wandb_path is not None:
        download_from_wandb(wandb_path=args.wandb_path, output_zipname=args.output)
    else:
        raise ValueError(
            "Please provide either --codebase, --wandb_artifact, or --wandb_path"
        )


if __name__ == "__main__":
    main()
