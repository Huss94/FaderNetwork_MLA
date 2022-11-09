import tensorflow as tf
from tensorflow import keras
import argparse
import cv2 as cv
import numpy as np 
import os 
from loader import Loader
from model import Fader
from utils import hstack, load_model , denormalize, vstack


parser = argparse.ArgumentParser(description='Use the trained fader network on some images')
parser.add_argument("--model_path", type = str, default = 'models/Ae', help = "Chemin du fader network entrainé")
parser.add_argument("--img_path", type = str, default = "data/img_align_celeba_resized", help= "Path to images. It can be the directory of the image, or the npz file")
parser.add_argument("--attr_path" ,type = str, default = "data/attributes.npz", help = "path to attributes")
parser.add_argument("--n_images_to_infer", type = int, default = '5', help = "Nombre d'image a inférer")
parser.add_argument("--n_alphas", type = int, default = '10', help = "Nombre d'image a inférer")
parser.add_argument("--indices", type = str, default = None, help  = "Listes d'indices d'images a traiter. Si cette arguments et donné, inutile de donner n_images_to_infer")
parser.add_argument("--load_in_ram", type= bool, default = False, help = "Si l'ordinateur n'a pas assez de ram pour charger toutes les données en meme temps, mettre False, le programme chargera seuleemnt les batchs de taille défini (32 par default) puis les déchargera après le calcul effectué") 
parser.add_argument("--n_images", type = int, default = 202599, help = "Number of images in the dataset")
parser.add_argument("--offset", type = int, default = 0, help = "Décalage dans la base de test")
parser.add_argument("--save_path", type = str, default = "images", help = "Chemin de sauvegarde l'image")
parser.add_argument("--hasardous_indices", type = bool, default = True, help = "Défini si on prend des données hasardeuse dans la base de test")
params = parser.parse_args()


#Paramètres
ae = load_model(params.model_path, model_type = 'ae')

bs = params.n_images_to_infer
n_alphas = params.n_alphas
params.attr = ae.params.attr
params.resize = ae.params.resize



"""
Il est dit dans le papier que les attributs de forme [0, 1] ou [1, 0] n'ont pas besoind d'être binaire
Par exmple on peut créer une image avec l'attribut Male [0.2,  0.8], la célébrité sera alors "un homme a 80%" selon le newtork 

On va alors créer un tableau de facteur alpha allant de 0 a 1 dont la taille minimum du tableau est 2
"""

# Les auteurs ont utilisé un alpha_min et un alpha_max, je comprnds pas encore pourquoi, on verra lors des tests
alphas = np.linspace(0, 1, n_alphas)
alphas = [[1-a, a] for a in alphas]

Data = Loader(params)

if params.hasardous_indices:
    params.indices = np.random.randint(Data.val_indices, Data.test_indices, bs)
#Chargement des images 
# On ne teste que sur la base de test que le reseau n'a jamais vu

if params.indices is not None: 
    print(params.indices)
    indices = np.array(params.indices)
    assert (indices >= Data.val_indices).all() and (indices <= Data.test_indices).all()
    x,y = Data.load_batch(params.indices)
else: 
    ind_min = Data.val_indices + params.offset
    ind_max = ind_min + params.n_images_to_infer
    assert ind_min >= Data.val_indices
    assert ind_max <= Data.test_indices 

    x,y = Data.load_batch_sequentially(ind_min,ind_max)


z = ae(x)
original_images = denormalize(x)
infered_images = []


for a in alphas:
    a = np.expand_dims(a, 0).astype(np.float32)
    alpha = np.repeat(a, bs, axis = 0)
    recons_images = denormalize(ae.decode(z, alpha))
    infered_images.append(recons_images)


col = []
im = []
for k in original_images:
    im = vstack(im, k)
col.append(im)

for im_alpha in infered_images:
    im = []
    for j in range(bs):
        im = vstack(im,im_alpha[j] )
    col.append(im)

final_image = []
for j in range(len(col)):
    final_image = hstack(final_image, col[j])

if not os.path.isdir(params.save_path):
    os.mkdir(params.save_path)

cv.imwrite(params.save_path + '/infered.jpg', final_image)
        