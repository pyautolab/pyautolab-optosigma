from pathlib import Path

import pyautolab_OptoSigma

optosigma_path = Path(pyautolab_OptoSigma.__file__).parent

datas = []
datas += [(str(optosigma_path), "pyautolab_OptoSigma")]
