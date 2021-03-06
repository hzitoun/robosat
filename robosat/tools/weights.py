import os
import argparse

import numpy as np
from tqdm import tqdm

import torch
from torch.utils.data import DataLoader
from torchvision.transforms import Compose

from robosat.config import load_config
from robosat.datasets import SlippyMapTiles
from robosat.transforms import MaskToTensor


def add_parser(subparser):
    parser = subparser.add_parser(
        "weights", help="computes class weights on dataset", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--config", type=str, required=True, help="path to configuration file")

    parser.set_defaults(func=main)


def main(args):
    config = load_config(args.config)
    path = config["dataset"]["path"]
    num_classes = len(config["classes"]["titles"])

    train_transform = Compose([MaskToTensor()])
    train_dataset = SlippyMapTiles(os.path.join(path, "training", "labels"), "mask", transform=train_transform)

    n = 0
    counts = np.zeros(num_classes, dtype=np.int64)

    loader = DataLoader(train_dataset, batch_size=1)
    for images, tile in tqdm(loader, desc="Loading", unit="image", ascii=True):
        image = torch.squeeze(images)

        image = np.array(image, dtype=np.uint8)
        n += image.shape[0] * image.shape[1]
        counts += np.bincount(image.ravel(), minlength=num_classes)

    assert n > 0, "dataset with masks must not be empty"

    # Class weighting scheme `w = 1 / ln(c + p)` see:
    # - https://arxiv.org/abs/1707.03718
    #     LinkNet: Exploiting Encoder Representations for Efficient Semantic Segmentation
    # - https://arxiv.org/abs/1606.02147
    #     ENet: A Deep Neural Network Architecture for Real-Time Semantic Segmentation

    probs = counts / n
    weights = 1 / np.log(1.02 + probs)

    weights.round(6, out=weights)
    print(weights.tolist())
