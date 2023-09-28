# Codesave

### Installation:

```
pip install git+https://github.com/dibyaghosh/codesave.git
```

### Basic Usage

The easiest way to use codesave is using `checkpoint_codebase`, which will take all the files in the directory and create a zip file.

For example, suppose we have some repository with the following structure:

    codebase/
        src/
            model.py
            utils.py
        train.py
        eval.py

```
from codesave import checkpoint_codebase
checkpoint_codebase('codebase/', output_zipname='codebase.zip')
```

Then, anywhere else  (even if we don't have codesave installed), we can do:

```
import sys
sys.path.append('codebase.zip')
import src.model # This will load the library directly from the zip file
```

### Loading multiple versions of a codebase

We can even load multiple versions of a codebase (this requires codesave to be installed though)

```
from codesave import ZipCodebase
codebase1 = ZipCodebase('codebase.zip')
codebase2 = ZipCodebase('codebase_v2.zip')
codebase1._from('src', 'model' _as='model_v1')
# equivalent to (from src import model as model_v1) from codebase.zip
codebase2._from('src', 'model' _as='model_v2')
# equivalent to (from src import model as model_v2) from codebase_v2.zip
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
