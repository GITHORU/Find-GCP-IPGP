#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Script to merge multiple MicMac SetOfMesureAppuisFlottants XML files (S2D format)
with optional filtering by point names (whitelist/blacklist)

Usage:
    python merge_micmac_xml.py -o output.xml input1.xml input2.xml ...
    python merge_micmac_xml.py -o output.xml --keep 12,14,15 input1.xml input2.xml
    python merge_micmac_xml.py -o output.xml --exclude 58,63 input1.xml input2.xml
"""
import sys
import os
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict, OrderedDict

def parse_xml_file(xml_file):
    """Parse a MicMac SetOfMesureAppuisFlottants XML file (S2D format)
    
    :param xml_file: path to XML file
    :return: dictionary of {image_name: {point_id: (x, y)}}
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing {xml_file}: {e}", file=sys.stderr)
        return {}
    except FileNotFoundError:
        print(f"File not found: {xml_file}", file=sys.stderr)
        return {}
    
    if root.tag != 'SetOfMesureAppuisFlottants':
        print(f"Warning: {xml_file} does not have SetOfMesureAppuisFlottants root element", file=sys.stderr)
        return {}
    
    images_data = defaultdict(dict)
    
    for image_elem in root.findall('MesureAppuiFlottant1Im'):
        name_im_elem = image_elem.find('NameIm')
        if name_im_elem is None:
            print(f"Warning: Missing NameIm in {xml_file}, skipping image", file=sys.stderr)
            continue
        
        image_name = name_im_elem.text
        
        for measure_elem in image_elem.findall('OneMesureAF1I'):
            name_pt_elem = measure_elem.find('NamePt')
            pt_im_elem = measure_elem.find('PtIm')
            
            if name_pt_elem is None or pt_im_elem is None:
                print(f"Warning: Invalid OneMesureAF1I in {xml_file} for image {image_name}, skipping", file=sys.stderr)
                continue
            
            point_id = name_pt_elem.text
            pt_coords = pt_im_elem.text.strip()
            
            # Parse coordinates (x y)
            try:
                coords = pt_coords.split()
                if len(coords) >= 2:
                    x = float(coords[0])
                    y = float(coords[1])
                    
                    if point_id in images_data[image_name]:
                        print(f"Warning: Duplicate point {point_id} in image {image_name} in {xml_file}, keeping first occurrence", file=sys.stderr)
                    else:
                        images_data[image_name][point_id] = (x, y)
                else:
                    print(f"Warning: Invalid coordinates format in {xml_file} for point {point_id} in image {image_name}", file=sys.stderr)
            except ValueError:
                print(f"Warning: Non-numerical coordinates in {xml_file} for point {point_id} in image {image_name}", file=sys.stderr)
    
    return dict(images_data)

def merge_xml_files(xml_files, keep_list=None, exclude_list=None):
    """Merge multiple XML files into one dictionary
    
    :param xml_files: list of XML file paths
    :param keep_list: list of point names to keep (whitelist), None for all
    :param exclude_list: list of point names to exclude (blacklist), None for none
    :return: merged dictionary of {image_name: {point_id: (x, y)}}
    """
    all_images_data = defaultdict(dict)
    
    # Convert keep_list and exclude_list to sets for faster lookup
    keep_set = set(keep_list) if keep_list else None
    exclude_set = set(exclude_list) if exclude_list else None
    
    for xml_file in xml_files:
        if not os.path.isfile(xml_file):
            print(f"Warning: {xml_file} does not exist, skipping", file=sys.stderr)
            continue
        
        images_data = parse_xml_file(xml_file)
        
        for image_name, points in images_data.items():
            for point_id, coords in points.items():
                # Apply filters
                if keep_set is not None and point_id not in keep_set:
                    continue
                if exclude_set is not None and point_id in exclude_set:
                    continue
                
                # If point already exists in this image, keep the first one
                if point_id in all_images_data[image_name]:
                    print(f"Warning: Point {point_id} already exists in image {image_name}, keeping first occurrence", file=sys.stderr)
                else:
                    all_images_data[image_name][point_id] = coords
    
    return dict(all_images_data)

def write_xml_output(images_data, output_file):
    """Write merged points to XML file (S2D format)
    
    :param images_data: dictionary of {image_name: {point_id: (x, y)}}
    :param output_file: output XML file path
    """
    root = ET.Element('SetOfMesureAppuisFlottants')
    
    # Sort images by name for consistent output
    for image_name in sorted(images_data.keys()):
        image_elem = ET.SubElement(root, 'MesureAppuiFlottant1Im')
        
        name_im_elem = ET.SubElement(image_elem, 'NameIm')
        name_im_elem.text = image_name
        
        # Sort points by ID for consistent output
        for point_id in sorted(images_data[image_name].keys(), key=lambda x: (len(x), x) if x.isdigit() else (999999, x)):
            x, y = images_data[image_name][point_id]
            
            measure_elem = ET.SubElement(image_elem, 'OneMesureAF1I')
            
            name_pt_elem = ET.SubElement(measure_elem, 'NamePt')
            name_pt_elem.text = str(point_id)
            
            pt_im_elem = ET.SubElement(measure_elem, 'PtIm')
            # Format coordinates with high precision as in MicMac format
            pt_im_elem.text = f"{x:.14f} {y:.14f}"
    
    tree = ET.ElementTree(root)
    ET.indent(tree, space="     ")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" ?>\n')
            tree.write(f, encoding='unicode', xml_declaration=False)
        
        total_points = sum(len(points) for points in images_data.values())
        print(f"Successfully wrote {len(images_data)} images with {total_points} total points to {output_file}", file=sys.stderr)
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)

def parse_list(list_str):
    """Parse comma-separated list string
    
    :param list_str: comma-separated string
    :return: list of strings (stripped)
    """
    if not list_str:
        return None
    return [item.strip() for item in list_str.split(',') if item.strip()]

def main():
    parser = argparse.ArgumentParser(
        description='Merge multiple MicMac SetOfMesureAppuisFlottants XML files (S2D format)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge all files
  python merge_micmac_xml.py -o merged.xml file1.xml file2.xml file3.xml
  
  # Keep only specific points
  python merge_micmac_xml.py -o merged.xml --keep 12,14,15 file1.xml file2.xml
  
  # Exclude specific points
  python merge_micmac_xml.py -o merged.xml --exclude 58,63 file1.xml file2.xml
  
  # Combine keep and exclude (keep takes precedence)
  python merge_micmac_xml.py -o merged.xml --keep 12,14,15 --exclude 58 file1.xml file2.xml
        """
    )
    
    parser.add_argument('input_files', nargs='+', metavar='XML_FILE',
                       help='Input XML files to merge')
    parser.add_argument('-o', '--output', required=True,
                       help='Output XML file path')
    parser.add_argument('--keep', type=str, default=None,
                       help='Comma-separated list of point names to keep (whitelist)')
    parser.add_argument('--exclude', type=str, default=None,
                       help='Comma-separated list of point names to exclude (blacklist)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Parse filter lists
    keep_list = parse_list(args.keep)
    exclude_list = parse_list(args.exclude)
    
    if args.verbose:
        print(f"Input files: {args.input_files}", file=sys.stderr)
        if keep_list:
            print(f"Keep list: {keep_list}", file=sys.stderr)
        if exclude_list:
            print(f"Exclude list: {exclude_list}", file=sys.stderr)
    
    # Merge XML files
    merged_images = merge_xml_files(args.input_files, keep_list, exclude_list)
    
    if not merged_images:
        print("No images or points to write. Check input files and filters.", file=sys.stderr)
        sys.exit(1)
    
    # Write output
    write_xml_output(merged_images, args.output)
    
    if args.verbose:
        print(f"Merged {len(merged_images)} images:", file=sys.stderr)
        for image_name in sorted(merged_images.keys()):
            points = merged_images[image_name]
            print(f"  - {image_name}: {len(points)} points", file=sys.stderr)
            for point_id in sorted(points.keys()):
                print(f"    * {point_id}", file=sys.stderr)

if __name__ == "__main__":
    main()
