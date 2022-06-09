import argparse
import sys
import os
import json
import shutil
import cv2
import xml.etree.ElementTree as ET

def make_parser():
    parser = argparse.ArgumentParser('Python Skill Evaluation')
    parser.add_argument("--imagedir", type=str, default='./images')
    parser.add_argument("--xmldir", type=str, default='./xmldata')
    parser.add_argument("--outputdir", type=str, default='./output')
    return parser

START_BOUNDING_BOX_ID = 1
PRE_DEFINE_CATEGORIES = {}


def get(root, name):
    vars = root.findall(name)
    return vars


def get_and_check(root, name, length):
    vars = root.findall(name)
    if len(vars) == 0:
        raise NotImplementedError('Can not find %s in %s.'%(name, root.tag))
    if length > 0 and len(vars) != length:
        raise NotImplementedError('The size of %s is supposed to be %d, but is %d.'%(name, length, len(vars)))
    if length == 1:
        vars = vars[0]
    return vars


def get_filename_as_int(filename):
    try:
        filename = os.path.splitext(filename)[0]
        return int(filename)
    except:
        raise NotImplementedError('Filename %s is supposed to be an integer.'%(filename))


def convert(args, xml_list, xml_dir, json_file):
    list_fp = open(xml_list, 'r')
    json_dict = {"images":[], "type": "instances", "annotations": [],
                 "categories": []}
    categories = PRE_DEFINE_CATEGORIES
    bnd_id = START_BOUNDING_BOX_ID
    for line in list_fp:
        line = line.strip()
        print("Processing %s"%(line))
        xml_f = os.path.join(xml_dir, line)
        tree = ET.parse(xml_f)
        root = tree.getroot()
        path = get(root, 'path')
        if len(path) == 1:
            filename = os.path.basename(path[0].text)
        elif len(path) == 0:
            filename = get_and_check(root, 'filename', 1).text
        else:
            raise NotImplementedError('%d paths found in %s'%(len(path), line))
        ## The filename must be a number
        image_id = get_filename_as_int(filename)
        size = get_and_check(root, 'size', 1)
        width = int(get_and_check(size, 'width', 1).text)
        height = int(get_and_check(size, 'height', 1).text)
        # resize images if dimensions exceed 800px (width) x 450px (height)
        img_path = os.path.join(args.imagedir, filename)
        output_path = os.path.join(args.outputdir, filename)
        width_ratio = float(width) / 800
        height_ratio = float(height) / 450
        ratio = 1.
        if width_ratio > 1. or height_ratio > 1.:
            img = cv2.imread(img_path)
            if width_ratio > height_ratio:
                ratio = width_ratio
                new_height = int(float(height) / width_ratio)
                new_width = 800
                resized = cv2.resize(img, (new_width, new_height))
                image = {'file_name': filename, 'height': new_height, 'width': new_width, 'id':image_id}
            else:
                ratio = height_ratio
                new_height = 450
                new_width = int(float(width) / height_ratio)
                resized = cv2.resize(img, (new_width, new_height))
                image = {'file_name': filename, 'height': new_height, 'width': new_width, 'id':image_id}
            # save the final images that are resized
            cv2.imwrite(output_path, resized)
        else:
            # save the final images that are not resized
            shutil.copyfile(img_path, output_path)
            image = {'file_name': filename, 'height': height, 'width': width, 'id':image_id}
        json_dict['images'].append(image)
        ## Cruuently we do not support segmentation
        #  segmented = get_and_check(root, 'segmented', 1).text
        #  assert segmented == '0'
        for obj in get(root, 'object'):
            category = get_and_check(obj, 'name', 1).text
            if category not in categories:
                new_id = len(categories)
                categories[category] = new_id
            category_id = categories[category]
            bndbox = get_and_check(obj, 'bndbox', 1)
            # recalculates the coordinates of the bounding boxes of annotated objects to adapt them to the new dimensions of the image, if it has been resized
            xmin = int((int(get_and_check(bndbox, 'xmin', 1).text) - 1) / ratio)
            ymin = int((int(get_and_check(bndbox, 'ymin', 1).text) - 1) / ratio)
            xmax = int(int(get_and_check(bndbox, 'xmax', 1).text) / ratio)
            ymax = int(int(get_and_check(bndbox, 'ymax', 1).text) / ratio)
            assert(xmax > xmin)
            assert(ymax > ymin)
            o_width = abs(xmax - xmin)
            o_height = abs(ymax - ymin)
            ann = {'area': o_width*o_height, 'iscrowd': 0, 'image_id':
                   image_id, 'bbox':[xmin, ymin, o_width, o_height],
                   'category_id': category_id, 'id': bnd_id, 'ignore': 0,
                   'segmentation': []}
            json_dict['annotations'].append(ann)
            bnd_id = bnd_id + 1

    for cate, cid in categories.items():
        cat = {'supercategory': 'none', 'id': cid, 'name': cate}
        json_dict['categories'].append(cat)
    json_fp = open(json_file, 'w')
    json_str = json.dumps(json_dict)
    json_fp.write(json_str)
    json_fp.close()
    list_fp.close()

if __name__ == "__main__":
    args = make_parser().parse_args()
    with open('xml.txt', 'w') as f:
        for filename in os.listdir(args.xmldir):
            f.write(filename + '\n')
    convert(args, './xml.txt', args.xmldir, args.outputdir + '/output.json')
        
