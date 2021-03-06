#!/usr/bin/env python
import sys
import os
import os.path as osp
import numpy as np
import json

import _init_paths
from caffe_feature_extractor import CaffeFeatureExtractor

from numpy.linalg import norm


def process_image_list(feat_extractor, prob_thresh,
                       last_new_id, new_id_map,
                       calc_orig_label_prob,
                       save_dir,
                       out_fp1, out_fp2,
                       img_list, label_list=None,
                       image_dir=None,
                       mirror_input=False):

    ftrs = feat_extractor.extract_features_for_image_list(
        img_list, image_dir, mirror_input=mirror_input)
#    np.save(osp.join(save_dir, save_name), ftrs)
    feat_layer_names = feat_extractor.get_feature_layers()

    feat_layer = feat_layer_names[0]
    corr_prob_layer = feat_layer_names[1]

    # print '===> Processing image batch with {} images'.format(len(img_list))
    # print 'feat_layer name: ', feat_layer
    # print 'corr_prob_layer name: ', corr_prob_layer

    for i, img_fn in enumerate(img_list):
        # print '---> image: ' + img_fn
        spl = osp.split(img_fn)
        base_name = spl[1]
#        sub_dir = osp.split(spl[0])[1]
        sub_dir = spl[0]

        for layer in feat_layer_names:
            # skip orignal layer, cause we'll norm it before saving
            if layer is corr_prob_layer:
                continue

            if sub_dir:
                save_sub_dir = osp.join(save_dir, layer, sub_dir)
            else:
                save_sub_dir = osp.join(save_dir, layer)

            if not osp.exists(save_sub_dir):
                os.makedirs(save_sub_dir)

            # print 'ftrs[{}].shape: {}'.format(layer, ftrs[layer].shape)

            save_name = osp.splitext(base_name)[0] + '.npy'
            np.save(osp.join(save_sub_dir, save_name), ftrs[layer][i])

        # calculate correlation probs
        feat = np.ravel(ftrs[feat_layer][i])
        feat_norm = norm(feat)
        probs = np.ravel(ftrs[corr_prob_layer][i]) / feat_norm

        # print 'probs.shape:', probs.shape

        sub_dir_0 = 'corr_prob'
        if sub_dir:
            save_sub_dir = osp.join(save_dir, sub_dir_0, sub_dir)
        else:
            save_sub_dir = osp.join(save_dir, sub_dir_0)

        if not osp.exists(save_sub_dir):
            os.makedirs(save_sub_dir)

        save_name = osp.splitext(base_name)[0] + '.npy'
        np.save(osp.join(save_sub_dir, save_name), probs)

        # if label_list:
        #     print 'original label: ', label_list[i]
        #     if calc_orig_label_prob:
        #         print 'prob[orig_label]: ', probs[label_list[i]]

        max_label = np.argmax(probs)
        # print 'max_label=%5d, probs[max_label]=%.4f' % (max_label,
        # probs[max_label])

        new_label = -1

        if probs[max_label] >= prob_thresh:
            new_label = max_label
        elif label_list:
            if new_id_map[label_list[i]] < 0:
                last_new_id += 1
                new_id_map[label_list[i]] = last_new_id

            new_label = new_id_map[label_list[i]]

        write_string = "%s\t%5d\t%5d\t%.4f" % (
            img_fn, new_label, max_label, probs[max_label])

        if label_list:
            write_string += "\t%5d" % (label_list[i])
            if calc_orig_label_prob:
                write_string += "\t%.4f" % (probs[label_list[i]])

        write_string += '\n'

        if probs[max_label] < prob_thresh:
            out_fp1.write(write_string)
        else:
            out_fp2.write(write_string)

    return last_new_id


def extract_probs_and_refine_labels(config_json, prob_thresh,
                                    first_new_id, max_orig_label,
                                    image_list_file, image_dir,
                                    save_dir=None, num_images=-1,
                                    mirror_input=False):

    if not save_dir:
        save_dir = 'rlt_probs_and_refined_labels'

    if not osp.exists(save_dir):
        os.makedirs(save_dir)

    new_id_map = np.ones(max_orig_label + 1, dtype=np.int32) * (-1)

    calc_orig_label_prob = (first_new_id == 0)

    output_fn_prefix = 'prob_thresh_%g' % prob_thresh

    # test extract_features_for_image_list()
    output_fn1 = output_fn_prefix + '-nonoverlap-img_list.txt'
    output_fp1 = open(osp.join(save_dir, output_fn1), 'w')
    output_fn2 = output_fn_prefix + '-overlap-img_list.txt'
    output_fp2 = open(osp.join(save_dir, output_fn2), 'w')

    output_fp1.write(
        'image_name        new_label  max_label  prob[max_label]  orig_label  prob[orig_label]\n')
    output_fp2.write(
        'image_name        new_label  max_label  prob[max_label]  orig_label  prob[orig_label]\n')

    fp = open(image_list_file, 'r')

    # init a feat_extractor
    print '\n===> init a feat_extractor'

    feat_extractor = CaffeFeatureExtractor(config_json)
    batch_size = feat_extractor.get_batch_size()
    # overwrite 'feature_layer' in config by the last layer's name
    # prob_layer = feat_extractor.get_final_layer_name()
    # print '===> prob layer name: ', prob_layer
    # feat_extractor.set_feature_layers(prob_layer)

    print 'feat_extractor can process %5d images in a batch' % batch_size

    img_list = []
    label_list = []

    ttl_img_cnt = 0
    batch_img_cnt = 0
    batch_cnt = 0

    last_new_id = first_new_id - 1

    for line in fp:
        if line.startswith('#'):
            continue

        spl = line.split()
        img_list.append(spl[0].strip())

        if (len(spl) > 1):
            label_list.append(int(spl[1]))

        batch_img_cnt += 1
        ttl_img_cnt += 1

        if batch_img_cnt == batch_size or (num_images > 0 and ttl_img_cnt == num_images):
            batch_cnt += 1
            print '\n===> Processing batch #%5d with %5d images' % (batch_cnt, batch_img_cnt)

            last_new_id = process_image_list(feat_extractor, prob_thresh,
                                             last_new_id, new_id_map,
                                             calc_orig_label_prob,
                                             save_dir,
                                             output_fp1, output_fp2,
                                             img_list, label_list,
                                             image_dir, mirror_input)
            batch_img_cnt = 0
            img_list = []
            label_list = []

            output_fp1.flush()
            output_fp2.flush()

        if (num_images > 0 and ttl_img_cnt == num_images):
            break

    if batch_img_cnt > 0:
        batch_cnt += 1
        print '\n===> Processing batch #%5d with %5d images' % (batch_cnt, batch_img_cnt)
        last_new_id = process_image_list(feat_extractor, prob_thresh,
                                         last_new_id, new_id_map,
                                         calc_orig_label_prob,
                                         save_dir,
                                         output_fp1, output_fp2,
                                         img_list, label_list,
                                         image_dir, mirror_input)

    fp.close()

    output_fp1.close()
    output_fp2.close()

    new_id_map_fn = output_fn_prefix + '-nonoverlap-new_id_map.npy'
    new_id_map_fn = osp.join(save_dir, new_id_map_fn)
    np.save(new_id_map_fn, new_id_map)


if __name__ == '__main__':

    config_json = './extractor_config_sphere64_webface.json'

    prob_thresh = 0.55
    first_new_id = 10572
    max_orig_label = 2

    # image path: osp.join(image_dir, <each line in image_list_file>)
    image_dir = r'../../test_data/face_chips'
    image_list_file = r'../../test_data/face_chips_list_with_label.txt'

    save_dir = 'rlt_probs_and_refined_labels'
    num_images = -1
    mirror_input = False

    extract_probs_and_refine_labels(config_json, prob_thresh,
                                    first_new_id, max_orig_label,
                                    image_list_file, image_dir,
                                    save_dir, num_images, mirror_input)
