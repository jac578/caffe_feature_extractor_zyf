#! /usr/bin/env python
import _init_paths
import sys
from extract_features_facescrub import extract_features


if __name__ == '__main__':
    config_json = './extractor_config_sphere64_pod.json'
    save_dir = '/workspace/data/megaface-eval/features/sphereface-64-ms--fixed2-0107/FaceScrub_SPF512Features'
    gpu_id = None

    if len(sys.argv) > 1:
        gpu_id = int(sys.argv[1])

    # image path: osp.join(image_dir, <each line in image_list_file>)
    image_dir = r'/workspace/code/mtcnn-caffe-zyf/scripts/face_aligner/facescrub_mtcnn_aligned/aligned_imgs'
    image_list_file = r'/workspace/code/mtcnn-caffe-zyf/scripts/face_aligner/facescrub_mtcnn_aligned/facescrub-aligned-image-list-0130.txt'
    extract_features(config_json, save_dir, image_list_file, image_dir, gpu_id=gpu_id)
