# USAGE
# python crop_accuracy.py

# import the necessary packages
from config import config as config
from mlib.preprocessing import ImageToArrayPreprocessor
from mlib.preprocessing import SimplePreprocessor
from mlib.preprocessing import MeanPreprocessor
from mlib.preprocessing import CropPreprocessor
from mlib.io import HDF5DatasetGenerator
from mlib.utils.ranked import rank5_accuracy
from tensorflow.keras.models import load_model
import numpy as np
import progressbar
import json

from sklearn.metrics import classification_report
from sklearn.metrics import accuracy_score

# load the RGB means for the training set
means = json.loads(open(config.DATASET_MEAN).read())

# initialize the image preprocessors
sp = SimplePreprocessor(227, 227)
mp = MeanPreprocessor(means["R"], means["G"], means["B"])
cp = CropPreprocessor(227, 227)
iap = ImageToArrayPreprocessor()

# load the pretrained network
print("[INFO] loading model...")
model = load_model(config.MODEL_PATH)

# initialize the testing dataset generator, then make predictions on
# the testing data
print("[INFO] predicting on test data (no crops)...")
testGen = HDF5DatasetGenerator(config.TEST_HDF5, 15,
	preprocessors=[sp, mp, iap], classes=3)
predictions = model.predict(testGen.generator(),
	steps=testGen.numImages // 15, max_queue_size=10)

print(testGen.numImages)

# compute the rank-1 and rank-5 accuracies
(rank1, _) = rank5_accuracy(predictions, testGen.db["labels"])
print("[INFO] rank-1: {:.2f}%".format(rank1 * 100))

#print(predictions.shape)
#print(predictions[:1])
#print(predictions)

# generate a classification report for the model
# print("[INFO] evaluating...")
# preds = model.predict(db["features"][i:])
# print(classification_report(db["labels"][i:], preds, target_names=db["label_names"]))
# print(classification_report(testGen.db["labels"], predictions))

# compute the raw accuracy with extra precision
#acc = accuracy_score(db["labels"][i:], preds)
#print("[INFO] score: {}".format(acc))

testGen.close()

# re-initialize the testing set generator, this time excluding the
# `SimplePreprocessor`
testGen = HDF5DatasetGenerator(config.TEST_HDF5, 15,
	preprocessors=[mp], classes=3)
predictions = []

# initialize the progress bar
widgets = ["Evaluating: ", progressbar.Percentage(), " ",
	progressbar.Bar(), " ", progressbar.ETA()]
pbar = progressbar.ProgressBar(maxval=testGen.numImages // 15,
	widgets=widgets).start()

# loop over a single pass of the test data
for (i, (images, labels)) in enumerate(testGen.generator(passes=1)):
	# loop over each of the individual images
	for image in images:
		# apply the crop preprocessor to the image to generate 10
		# separate crops, then convert them from images to arrays
		crops = cp.preprocess(image)
		crops = np.array([iap.preprocess(c) for c in crops],
			dtype="float32")

  	# make predictions on the crops and then average them
		# together to obtain the final prediction
		pred = model.predict(crops)
		predictions.append(pred.mean(axis=0))

	# update the progress bar
	pbar.update(i)

# compute the rank-1 accuracy
pbar.finish()
print("[INFO] predicting on test data (with crops)...")
(rank1, _) = rank5_accuracy(predictions, testGen.db["labels"])
print("[INFO] rank-1: {:.2f}%".format(rank1 * 100))
testGen.close()

