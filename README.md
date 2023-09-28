# Codesave

### Installation:

```
pip install git+https://github.com/dibyaghosh/codesave.git
```

### Basic Usage

The easiest way to use codesave is using `checkpoint_codebase`, which will take all the files in the directory and create a zip file.

For example, suppose we have some repository with the following structure:

    codebase/
        model.py
        train.py
        eval.py

```
from codesave import checkpoint_codebase
checkpoint_codebase('codebase/', output_zipname='codesave.zip')
```

Then, anywhere else  (even if we don't have codesave installed), we can do:

```
import sys
sys.path.append('codesave.zip')
import model # This will load the library directly from the zip file
```

### Loading multiple versions of a codebase

We can even load multiple versions of a codebase (this requires codesave to be installed though)

```
from codesave import ZipCodebase
codebase1 = ZipCodebase('codesave.zip')
codebase2 = ZipCodebase('codesave_v2.zip')
codebase1._import('model', _as='model_v1')
# model_v1 is now the model library from codesave.zip
codebase2._import('model', _as='model_v2')
# model_v2 is now the model library from codesave_v2.zip
```

### Integration w/ wandb

When training,
```
from codesave import checkpoint_codebase_for_wandb
wandb.init(...)
checkpoint_codebase_for_wandb('codebase/')
```

Now at any point,
```
from codesave import load_codebase_from_wandb
load_codebase_from_wandb(wandb_run_name, output_zipname='codesave.zip')
# Now we can add to sys.path or ZipCodebase as before
```
