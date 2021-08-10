
from typing import List

from bs4 import BeautifulSoup

def destroy_unimportant_tags_inplace(soup_tag, tags_to_remove: List[str]):
    """Remove tags like <bold> or <italic>"""
    for tag_to_remove in tags_to_remove:
        for match in soup_tag.find_all(tag_to_remove):
            match.replaceWithChildren()


def create_new_parent_tag(soup_tag, parent_tag_name: str, soup):
    """Wraps soup tag with another parent tag"""
    new_parent_tag = soup.new_tag(parent_tag_name)
    contents = soup_tag.replace_with(new_parent_tag)
    new_parent_tag.append(contents)
    return new_parent_tag

