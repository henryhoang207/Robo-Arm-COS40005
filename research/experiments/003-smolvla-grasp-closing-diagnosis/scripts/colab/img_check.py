import numpy as np
from PIL import Image
b = np.asarray(Image.open("/content/out_t1/B_inputs.jpg").resize((640, 240)))
c = np.asarray(Image.open("/content/out_t1/C_inputs.jpg").resize((640, 240)))
Image.fromarray(np.concatenate([b[:, 320:], c[:, 320:]], 1)).save("/content/imgcheck.jpg")
