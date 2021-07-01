import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Tuple, List, Dict, Set, Any

from bs4 import BeautifulSoup, Tag

# To pull in this dependency, use "pip install -e ."
from annotation_store.plain_text_document import PlainTextDocument
from annotation_store.plain_text_annotations import PlainTextAnnotations, InputTextSpan


class XmlToAnnotatedDoc(ABC):

    def __init__(self, source):
        self.source = source

    @abstractmethod
    def on_start_tag(self, doc_text: str, context: List[Tag]) -> Tuple[str, bool]:
        """
        :param doc_text: The current document text
        :param context: The current set of ancestor XML elements, ending with the one being started
        :return: Tuple containing:
                The new document text
                True if this element should be converted into an annotation
        """
        pass

    @abstractmethod
    def on_text(self, doc_text: str, tag_text, context: List[Tag]) -> str:
        """
        :param doc_text: The current document text
        :param tag_text: The text element being processed
        :param context: The current set of ancestor XML elements
        :return: The new document text
        """
        pass

    @abstractmethod
    def on_end_tag(self, doc_text: str, context: List[Tag]) -> str:
        """
        :param doc_text: The current document text
        :param context: The current set of ancestor XML elements, ending with the one being ended
        :return: The new document text
        """
        pass

    def parse(self, xml) -> PlainTextDocument:
        text = ''
        annotations = defaultdict(list)
        context = []
        span_stack = []

        def traverse(element):
            nonlocal text
            if element.name is None:
                # Plain Text element
                text = self.on_text(text, element, context)
            else:
                context.append(element)
                text, create_annotation = self.on_start_tag(text, context)
                if create_annotation:
                    span_stack.append(
                        InputTextSpan(startChar=len(text), endChar=-1, attributes=element.attrs))
                for c in element.children:
                    traverse(c)
                if create_annotation:
                    span = span_stack.pop()
                    span.endChar = len(text)
                    annotations[element.name].append(span)
                text = self.on_end_tag(text, context)
                context.pop()

        traverse(xml)
        doc = PlainTextDocument(text, PlainTextAnnotations("header", {}, {}), self.source)
        for typ, spans in annotations.items():
            for span in spans:
                doc.annotate_span(typ, span)
        return doc

    def append_stripped_text(self, doc_text: str, text: str = "") -> str:
        return doc_text + text.strip()

    def append_text(self, doc_text: str, text: str = "") -> str:
        return doc_text + text

    def ignore_text(self, doc_text: str, text: str = "") -> str:
        return doc_text

    def add_linebreak(self, doc_text: str) -> str:
        return doc_text + '\n'

    def add_space(self, doc_text: str) -> str:
        return doc_text + ' '


class XmlToHeader(XmlToAnnotatedDoc):
    def __init__(self, source):
        super().__init__(source)
        self.annotations = {"title", "publisher", "abstract", "author", "forename", "surname",
                            "affiliation"}

        self.on_start_handler = {
            "title": self.add_linebreak,
            "author": self.add_linebreak,
            "affiliation": self.add_linebreak,
            "abstract": self.add_linebreak,
        }

        self.on_end_handler = {
            "orgName": self.add_linebreak,
            "forename": self.add_space,
            "surname": self.add_space,
            "email": self.add_space,
            "affiliation": self.add_linebreak,
            "title": self.add_linebreak,
            "publicationStmt": self.add_linebreak
        }

    def on_start_tag(self, doc_text: str, context: List[Tag]) -> Tuple[str, bool]:
        name = context[-1].name
        return (self.on_start_handler.get(name, self.ignore_text)(doc_text), name in self.annotations)

    def on_text(self, doc_text: str, tag_text, context: List[Tag]) -> str:
        if "encodingDesc" in (t.name for t in context):
            return doc_text
        return self.append_stripped_text(doc_text, tag_text)

    def on_end_tag(self, doc_text: str, context: List[Tag]) -> str:
        name = context[-1].name
        return self.on_end_handler.get(name, self.ignore_text)(doc_text)


class XmlToBody(XmlToAnnotatedDoc):
    def __init__(self, source):
        super().__init__(source)
        self.annotations = {"formula", "ref", "head", "figDesc", "table", "p", "label", "body",
                            "figure"}
        self.annotations = {"title", "publisher", "abstract", "author", "forename", "surname",
                            "affiliation"}

        self.on_start_handler = {
            "head": self.add_linebreak,
            "p": self.add_linebreak,
        }

        self.on_end_handler = {
            "head": self.add_linebreak,
            "p": self.add_linebreak,
        }

    def on_start_tag(self, doc_text: str, context: List[Tag]) -> Tuple[str, bool]:
        name = context[-1].name
        return (self.on_start_handler.get(name, self.ignore_text)(doc_text), name in self.annotations)

    def on_text(self, doc_text: str, tag_text, context: List[Tag]) -> str:
        return self.append_text(doc_text, tag_text)

    def on_end_tag(self, doc_text: str, context: List[Tag]) -> str:
        name = context[-1].name
        return self.on_end_handler.get(name, self.ignore_text)(doc_text)


class XmlToBibliography(XmlToAnnotatedDoc):
    def __init__(self, source):
        super().__init__(source)
        self.annotations = {
            "biblStruct", "author", "forename", "surname", "monogr", "meeting", "title", "biblScope"
        }

        self.on_start_handler = {
            "biblStruct": self.add_linebreak,
            "p": self.add_linebreak,
        }

        self.on_end_handler = {
            "biblStruct": self.add_linebreak,
            "title": self.add_linebreak,
            "forename": self.add_space,
            "surname": self.add_space,
        }

    def on_start_tag(self, doc_text: str, context: List[Tag]) -> Tuple[str, bool]:
        name = context[-1].name
        return (self.on_start_handler.get(name, self.ignore_text)(doc_text), name in self.annotations)

    def on_text(self, doc_text: str, tag_text, context: List[Tag]) -> str:
        return self.append_stripped_text(doc_text, tag_text)

    def on_end_tag(self, doc_text: str, context: List[Tag]) -> str:
        name = context[-1].name
        return self.on_end_handler.get(name, self.ignore_text)(doc_text)


def parse_file(file: str) -> Tuple[PlainTextDocument, PlainTextDocument, PlainTextDocument]:
    xml = BeautifulSoup(open(file, "rb").read(), "xml")

    header = XmlToHeader("doc2json-grobid").parse(xml.teiHeader)
    body = XmlToBody("doc2json-grobid").parse(xml.body)
    bib = XmlToBibliography("doc2json-grobid").parse(xml.back)
    for bib_item in bib.find("doc2json-grobid", "biblStruct")[:3]:
        authors = bib_item.find("doc2json-grobid", "author")
        print([(a.find("doc2json-grobid", "forename")[0].text, a.find("doc2json-grobid", "surname")[0].text) for a in authors])

    return (header, body, bib)


if __name__ == "__main__":
    parse_file(sys.argv[1])
