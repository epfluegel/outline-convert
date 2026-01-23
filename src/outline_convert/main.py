import argparse
import os
import sys
import xml.etree.ElementTree as ET
import zipfile
from contextlib import nullcontext
from doctest import debug
from typing import Optional, List

import pyperclip

from openai import OpenAI

from .models import Node
from .parser import parse_text, parse_opml
from .renderer_latex import render_latex_beamer, render_latex
from .renderer_text import render_text, render_opml
#from .utils import find_node, print_tree, ignore_forest, print_forest, filter, handle_ai_prompt, handle_ai_prompts
from .utils import find_node, print_tree, ignore_forest, print_forest, filter
from .renderer_ppt import render_ppt
from .renderer_rtf import render_rtf

# -- MAIN PROGRAM -----------------------------------------------------


def send_prompt(message, args:argparse.Namespace) -> str:
    # Initialize the client (make sure you set your OPENAI_API_KEY in environment variables)

    apiKey = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=apiKey)

    # model="gpt-5",  # or "gpt-4o-mini" if you prefer a lighter model
    aiModel = "gpt-4o-mini"
    #if "AI" in args.debug:
    print("using ", aiModel)
        
    # Send a prompt to the GPT model
    response = client.chat.completions.create(
        model=aiModel,  
        messages=[
            # {"role": "system", "content": "You are a helpful assistant that helps me with my math homework!"},
            {"role": "user", "content": message}
        ],
        temperature = 0, # no randomness
        top_p=1,         # disable nucleus sampling
        seed=42          # ensures same output across calls
    )

    # Extract and return the assistant’s reply
    return(response.choices[0].message.content)


def handle_ai_prompts(forest: List[Node], args: argparse.Namespace):
    retval = []
    for oneTree in forest:
        retval.append(handle_ai_prompt(oneTree, args))
    return(retval)
    
    
def handle_ai_prompt(node: Node, args: argparse.Namespace):
    if "#ai-prompt" in node.title:
        theForest = handle_ai_prompts(node.children, args)
        thePrompt = render_text(theForest, args) # TODO make args optional
        promptTxt = "\n".join(thePrompt)
        # print("thePrompt=", promptTxt)
        returnNode = Node(send_prompt(node.title + promptTxt, args))
        returnNode.children = []
    else:
        # return the tree with the same root but children handled recursively
        returnNode = Node(node.title)
        returnNode.children = handle_ai_prompts(node.children, args)
        
    return(returnNode)





def main():
    # -- Argument parser configuration -------------------------------
    p = argparse.ArgumentParser(description='Convert between text outline, OPML, and LaTeX')

    # Input/Output arguments
    p.add_argument('input', nargs='?', help='Input file (omit for stdin or use --date)')
    p.add_argument('-c', '--clipboard', action='store_true', help='Read from clipboard')
    p.add_argument('-o', '--output', help='Output filename (omit for auto)')
    p.add_argument('-d', '--dir', default='.', help='Output directory')

    # Metadata arguments
    p.add_argument('-e', '--email', help='Author email')
    p.add_argument('-a', '--author', help='Author name')
    p.add_argument('-g', '--graphicspath', help='Path to graphics')
    p.add_argument('-f', '--format', choices=['txt', 'opml', 'latex', 'beamer', 'ppt', 'rtf', 'docx'], default='txt',
                   help='Output format: plain text, OPML, LaTeX Article, LaTeX Beamer, PowerPoint, Rich Text')
    p.add_argument('-s', '--start', help='Start item for conversion')

    p.add_argument('-m', '--date', metavar='DIR',
                   help='Choose most recently modified file in directory DIR as input')
    p.add_argument('-z', nargs=2, metavar=('ZIP_DIRECTORY', 'PATH_TO_FILE_FROM_ZIP_FOLDER'),
                   help='Choose the selected file in the most recent zip backup')
    p.add_argument('--expert-mode', action='store_true',
                   help='Enter expert mode to interpret nodes tagged with specific labels, see readme')
    p.add_argument('-p', '--parse-markdown', action='store_true',
                   help='Parse markdown syntax for links and images')
    p.add_argument('--filter',
                   help='Filter a specific string and return the path to it')
    #p.add_argument('--biblio', nargs=1, metavar=('BIBTEX_FILE'),
    p.add_argument('--biblio',
                   help='Specify a fully qualified bibTex file name')


    # Output formatting arguments
    p.add_argument('--strip-tags', action='store_true', default=False, help='Strip tags from input')
    p.add_argument('--fragment', action='store_true', default=False, help='Only keep body of document for latex beamer and opml')
    p.add_argument('-w','--wait', action='store_true', default=False, help='Wait for key press after execution')
    p.add_argument('--debug', action='store_true', default=False, help='Gives debug information')
    p.add_argument('--test', action='store_true', default=False, help='Testing only, no output created')
    p.add_argument('--parse-only', action='store_true', default=False, help='Create parse tree only')
    p.add_argument('--add-new-line', action='store_true', default=False, help='Insert additional new line between items in output')
    p.add_argument('-t', '--indent-string', default="    ", help='Identation indent string used in output')
    p.add_argument('-n', '--include-notes', action='store_true', default=False, help='Include notes in ouput')
    p.add_argument('-b', '--bullet-symbol', default="", help="Symbol used for bullet points")
    p.add_argument( '--hide-completed',action='store_true', default=False, help="Hide completed items")
    p.add_argument( '--completed-only',action='store_true', default=False, help="Only includes completed items")

    args = p.parse_args()

    # -- Handle automatic date-based selection ----------------------
    if args.date:
        date_dir = args.date
        if not os.path.isdir(date_dir):
            sys.exit(f"Error: '{date_dir}' is not a directory.")
        candidates = [
            os.path.join(date_dir, name)
            for name in os.listdir(date_dir)
            if os.path.isfile(os.path.join(date_dir, name))
        ]
        if not candidates:
            sys.exit(f"No files found in '{date_dir}'.")
        chosen = max(candidates, key=lambda p: os.path.getmtime(p))
        if args.debug:
            print(f"Using latest file: {os.path.basename(chosen)}", file=sys.stderr)
        args.input = chosen

    if args.z:
        zip_dir = args.z[0]
        file = args.z[1]
              
        if not os.path.isdir(zip_dir):
            sys.exit(f"Error: '{zip_dir}' is not a directory.")
        chosen = None
        latest_time = 0

        for name in os.listdir(zip_dir):
            full_path = os.path.join(zip_dir, name)
            if zipfile.is_zipfile(full_path) and 'opml' in name:
                mtime = os.path.getmtime(full_path)
                if mtime > latest_time:
                    latest_time = mtime
                    chosen = full_path

        if not chosen:
            sys.exit(f"No correct zip files found in '{zip_dir}'.")
        if args.debug:
            print(f"Using latest zip file: {os.path.basename(chosen)}", file=sys.stderr)
        with zipfile.ZipFile(chosen, 'r') as zip_ref:
            with zip_ref.open(file) as f:
                lines = f.read().decode('utf-8').splitlines()

    # -- Read input data ------------------------------------------
    elif args.input:
        with open(args.input, 'r', encoding='utf-8') as file:
            lines = file.read().splitlines()
    elif args.clipboard:
        lines = pyperclip.paste().splitlines()
    else:
        print('Paste outline below. Finish with Ctrl+D (linux) or Ctrl+Z + Enter(Windows):')
        lines = sys.stdin.read().splitlines()

    # -- Parse content --------------------------------------------
    root_node: Node
    try:
        tree = ET.fromstringlist(lines)
        forest = ignore_forest(parse_opml(tree, args=args), args)
        print("ompl parsed correctly")

    except ET.ParseError:
        if args.debug:
            print("ompl not parsed correctly")
        forest = ignore_forest(parse_text(lines, args), args)


    # -- Optional subtree extraction ------------------------------

    if args.start:
        f = find_node(forest, args.start)
        forest = f
        if not forest:
            forest = [Node(f"Start prefix '{args.start}' not found")]
        elif args.debug:
            print(f"Start prefix '{args.start}' found")
            
        #print_forest(forest)
    if args.filter:
        forest = filter(forest, args.filter)
        if not forest:
            forest = [Node(f"Filter prefix '{args.filter}' not found")]
    # filter function can return filter not found if the start prefix was not found
    


    # deal with any AI prompt tags
    forest = handle_ai_prompts(forest, args)

    
    # -- Render based on chosen format ---------------------------
    out_lines: Optional[List[str]] = None
    out_tree: Optional[ET.ElementTree] = None
    if args.format == 'txt':
        tab=args.indent_string
        if tab == "\\t":
            tab = '\t'
        out_lines = render_text(forest, args)
    elif args.format == 'latex':
        out_lines = render_latex(forest, args)
    elif args.format == 'beamer':
        out_lines = render_latex_beamer(forest, args)
    elif args.format == 'opml':  # opml
        out_tree = render_opml(forest, args)
    elif args.format == 'ppt':
        out_lines = render_ppt(forest, args)
    elif args.format == 'rtf':
        out_lines = render_rtf(forest, args)

    # -- Handle output -------------------------------------------
    if args.clipboard:
        if out_lines is not None:
            pyperclip.copy('\n'.join(out_lines))
        else:
            xml_string = ET.tostring(out_tree, encoding='unicode')
            pyperclip.copy(xml_string)
        print("Copied to clipboard")

    elif not args.output:  # Output to stdout
        print("Output to stdout")
        #print(out_lines) so that we don't get confusing output
        if out_lines is not None:
            sys.stdout.write('\n'.join(out_lines) + '\n')
        else:
            out_tree.write(sys.stdout.buffer, encoding='utf-8', xml_declaration=True)
    else:  # Output to file
        os.makedirs(args.dir, exist_ok=True)
        path = os.path.join(args.dir, args.output)
        if out_lines is not None:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out_lines))
        else:
            out_tree.write(path, encoding='utf-8', xml_declaration=True)
        if args.debug:
            print(f"Wrote {path}")

    # -- Handle final wait --------------------------------------
    if args.wait:
        input("Press any Enter to exit\n")




if __name__ == '__main__':
    main()