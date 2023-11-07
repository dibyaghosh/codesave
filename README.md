# Codesave


## TL;DR

```bash
codesave . -o codebase.zip
code_from_wandb "wandb_username/project_name/run_id" -o codesave.zip 
```

```python
### When training
from codesave import checkpoint_to_wandb
wandb.init(...)
checkpoint_to_wandb(codebase_dirname)
# or wandb.run.log_code(codebase_dirname)

### Time to recover
from codesave import WandBCodebase
with WandBCodebase("wandb_username/project_name/run_id"):
    from src import model
    model.whatever_you_want
```

## Installation:

```
pip install codesave_library 
```

```
pip install git+https://github.com/dibyaghosh/codesave.git
```

## Basic Usage

The easiest way to use codesave is using `checkpoint` or `checkpoint_to_wandb`, which will take all the files in the directory and create a zip file.

For example, suppose we have some repository with the following structure:

    codebase/
        src/
            model.py
            utils.py
        train.py
        eval.py

```
from codesave import checkpoint, checkpoint_to_wandb
checkpoint('codebase/', output_zipname='codebase.zip')
checkpoint_to_wandb('codebase/') # Stores it in the current wandb run (on the cloud)
```

This creates a zipfile that we can use anywhere else  (even if we don't have codesave installed):

```
import sys
sys.path.append('codebase.zip')
import src.model # This will load the library directly from the zip file
```

## Loading a Codebase

### Using `sys.path`

The easiest way, doesn't require `codesave` to be installed

```python
import sys
sys.path.append('codebase.zip') # Or PYTHONPATH=codebase.zip:$PYTHONPATH
import src.model # This will load the library directly from the zip file
```

### Using `Codebase`

The second easiest way, but **cannot be run multiple times in the same process** (because old modules are not unloaded)

```python
from codesave import Codebase
with Codebase('codebase.zip'):
    from src import model
    model.whatever_you_want
```

### Using `UniqueCodebase` (general, recommended)

Using UniqueCodebase, we can load as many versions of a codebase as we want, and they can interact with each other.

The import notation is a little less clean, but it's necessary to avoid conflicts.

```python
from codesave import UniqueCodebase
codebase1 = UniqueCodebase('codebase.zip')
codebase2 = UniqueCodebase('codebase_v2.zip')
model_v1 = codebase1.import_module('src.model') # equivalent to (from src import model as model_v1) from codebase.zip
model_v2 = codebase2.import_module('src.model') # equivalent to (from src import model as model_v2) from codebase_v2.zip
```

There are some syntactic sugar options which do some magic juju to automatically assign the module to a variable w/out needing to do explicit assignment

```python
codebase1.import_('src.model') # equivalent to `import src.model`
codebase1.import_('src.model', as_='model_v1') # equivalent to `import src.model as model_v1`
codebase1.from_import('src', ('model', 'utils')) # equivalent to `from src import model, utils`
codebase1.from_import('src', 'model', as_='model_v1') # equivalent to `from src import model as model_v1`

```


### Just Unzip It

You can always unzip the zip file, and treat it as a normal directory.

## Integration w/ wandb

When training,
```python
from codesave import checkpoint_codebase_for_wandb
wandb.init(...)
checkpoint_codebase_for_wandb('codebase/')
```

Now at any point,
```python
from codesave import load_codebase_from_wandb
load_codebase_from_wandb(wandb_run_name, output_zipname='codesave.zip')
# Now we can add to sys.path or ZipCodebase as before
```

## API

```python
# These provide general routines to save codebase
from .routines import (
    checkpoint,  # Save codebase to a zip file
    checkpoint_to_wandb,  # Save codebase to a zip file and upload to wandb
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
```

```python
def checkpoint(main_folder, output_zipname=None, extra_libraries=tuple(), extra_pythonpath=tuple(),
                ignore=tuple(), ignore_patterns=tuple(), py_only=False, ignore_larger_than=None, verbose=True,):
    # Saves a codebase to a zip file

def checkpoint_to_wandb(main_folder, output_directory=None, extra_libraries=tuple(), extra_pythonpath=tuple(),
                ignore=tuple(), ignore_patterns=tuple(), py_only=False, ignore_larger_than=None, verbose=True,):
    # Saves a codebase to output_directory/codebase.zip file and uploads it to wandb
```