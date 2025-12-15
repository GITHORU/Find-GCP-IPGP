#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Script to merge multiple MicMac DicoAppuisFlottant XML files
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
from collections import OrderedDict

def parse_xml_file(xml_file):
    """Parse a MicMac DicoAppuisFlottant XML file
    
    :param xml_file: path to XML file
    :return: dictionary of {NamePt: {'Pt': coords, 'Incertitude': incertitude}}
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
    
    if root.tag != 'DicoAppuisFlottant':
        print(f"Warning: {xml_file} does not have DicoAppuisFlottant root element", file=sys.stderr)
        return {}
    
    points = {}
    for one_appui in root.findall('OneAppuisDAF'):
        name_pt_elem = one_appui.find('NamePt')
        pt_elem = one_appui.find('Pt')
        incertitude_elem = one_appui.find('Incertitude')
        
        if name_pt_elem is None or pt_elem is None:
            print(f"Warning: Invalid OneAppuisDAF in {xml_file}, skipping", file=sys.stderr)
            continue
        
        name_pt = name_pt_elem.text
        pt_coords = pt_elem.text
        incertitude = incertitude_elem.text if incertitude_elem is not None else "1 1 1"
        
        if name_pt in points:
            print(f"Warning: Duplicate point {name_pt} in {xml_file}, keeping first occurrence", file=sys.stderr)
        else:
            points[name_pt] = {
                'Pt': pt_coords,
                'Incertitude': incertitude
            }
    
    return points

def merge_xml_files(xml_files, keep_list=None, exclude_list=None):
    """Merge multiple XML files into one dictionary
    
    :param xml_files: list of XML file paths
    :param keep_list: list of point names to keep (whitelist), None for all
    :param exclude_list: list of point names to exclude (blacklist), None for none
    :return: merged dictionary of points
    """
    all_points = OrderedDict()
    
    # Convert keep_list and exclude_list to sets for faster lookup
    keep_set = set(keep_list) if keep_list else None
    exclude_set = set(exclude_list) if exclude_list else None
    
    for xml_file in xml_files:
        if not os.path.isfile(xml_file):
            print(f"Warning: {xml_file} does not exist, skipping", file=sys.stderr)
            continue
        
        points = parse_xml_file(xml_file)
        
        for name_pt, data in points.items():
            # Apply filters
            if keep_set is not None and name_pt not in keep_set:
                continue
            if exclude_set is not None and name_pt in exclude_set:
                continue
            
            # If point already exists, keep the first one (or could merge/average)
            if name_pt in all_points:
                print(f"Warning: Point {name_pt} already exists, keeping first occurrence", file=sys.stderr)
            else:
                all_points[name_pt] = data
    
    return all_points

def write_xml_output(points, output_file):
    """Write merged points to XML file
    
    :param points: dictionary of points
    :param output_file: output XML file path
    """
    root = ET.Element('DicoAppuisFlottant')
    
    # Sort points by name for consistent output
    for name_pt in sorted(points.keys()):
        one_appui = ET.SubElement(root, 'OneAppuisDAF')
        
        pt_elem = ET.SubElement(one_appui, 'Pt')
        pt_elem.text = points[name_pt]['Pt']
        
        name_pt_elem = ET.SubElement(one_appui, 'NamePt')
        name_pt_elem.text = name_pt
        
        incertitude_elem = ET.SubElement(one_appui, 'Incertitude')
        incertitude_elem.text = points[name_pt]['Incertitude']
    
    tree = ET.ElementTree(root)
    ET.indent(tree, space="     ")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" ?>\n')
            tree.write(f, encoding='unicode', xml_declaration=False)
        print(f"Successfully wrote {len(points)} points to {output_file}", file=sys.stderr)
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
        description='Merge multiple MicMac DicoAppuisFlottant XML files',
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
    merged_points = merge_xml_files(args.input_files, keep_list, exclude_list)
    
    if not merged_points:
        print("No points to write. Check input files and filters.", file=sys.stderr)
        sys.exit(1)
    
    # Write output
    write_xml_output(merged_points, args.output)
    
    if args.verbose:
        print(f"Merged {len(merged_points)} points:", file=sys.stderr)
        for name_pt in sorted(merged_points.keys()):
            print(f"  - {name_pt}", file=sys.stderr)

if __name__ == "__main__":
    main()

