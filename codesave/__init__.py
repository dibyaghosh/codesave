# These provide general routines to save codebase
from .routines import (
    checkpoint,  # Save codebase to a zip file
    checkpoint_to_wandb,  # Save codebase to a zip file and upload to wandb
    WandBCodebase,  # Load codebase directly from wandb
)

# These allow you to load a codebase from a zip file
from .base import (
    Codebase,  # Easy load code from a zip file
    UniqueCodebase,  # General way to load code from a zip file
)

# These are routines to download codebase from wandb
from .routines import (
    download_from_wandb,  # download something saved with checkpoint_to_wandb
    zip_from_wandb_artifact,  # download something saved with wandb.run.log_code
)
