import rdflib
from rdflib import URIRef, RDFS
import configparser
import pathlib
import os

from .node import Node

_classes_sparql = "SELECT ?cls ?sup WHERE { ?cls a owl:Class . OPTIONAL{ ?cls rdfs:subClassOf ?sup . } FILTER(?cls != owl:Thing)}"
_objects_sparql = "SELECT ?prop ?sup ?domain ?range WHERE { ?prop a owl:ObjectProperty . OPTIONAL{ ?prop rdfs:subPropertyOf ?sup .} OPTIONAL{ ?prop rdfs:domain ?domain. } OPTIONAL{ ?prop rdfs:range ?range. } FILTER(?prop != owl:topObjectProperty)}"
_data_sparql = "SELECT ?prop ?sup ?domain ?range WHERE { ?prop a owl:DatatypeProperty . OPTIONAL{ ?prop rdfs:subPropertyOf ?sup . } OPTIONAL{?prop rdfs:domain ?domain.} OPTIONAL{ ?prop rdfs:range ?range.} FILTER(?prop != owl:topDataProperty)}"

_ROOT = pathlib.Path(__file__).parent.parent.absolute()


def _get_rdfs_label(graph, subject, lang=None):
    subject = URIRef(subject)
    labels = []
    # setup the language filtering
    if lang is not None:
        if lang == "":  # we only want not language-tagged literals

            def langfilter(l):
                return l.language is None

        else:

            def langfilter(l):
                return l.language == lang

    else:  # we don't care about language tags

        def langfilter(l):
            return True

    for label in graph.objects(subject, RDFS.label):
        if langfilter(label):
            labels.append(str(label))
    return labels


class OntologyTrees:
    # Constrói três árvores, sendo elas (classes, object properties, data properties)
    # a partir de arquivo owl ou ttl no formato rdf
    def __init__(self, lang=None):
        self._roots = dict()
        self._trees = dict()
        self._max_depth = dict()
        self._trees_names = []
        self.lang = lang

        config = configparser.ConfigParser(delimiters="=")
        config.read(os.path.join(_ROOT, "properties_labels.ini"))
        self.properties_text = config["PROPERTIES"]

    def __grow_tree(self, graph, hierarchy_name, query_result):
        for row in query_result:
            node = Node(str(row[0]), str(row[1]))
            # Se o nó for de propriedades então busca o "label" no
            # arquivo de configurações "properties_labels.ini".
            if "properties" in hierarchy_name:
                if str(row[0]) in self.properties_text:
                    node.name = self.properties_text[str(row[0])]
                if row[2]:
                    node.add_domain(str(row[2]))
                if row[3]:
                    node.add_range(str(row[3]))
            else:
                # Se o nó for de classe, utiliza o rdfs label
                names = _get_rdfs_label(graph, str(row[0]), self.lang)
                if names:
                    node.name = names[0]
            self.__add_node(graph, hierarchy_name, node)

    def load_ontology(
        self,
        source=None,
        publicID=None,
        format=None,
        location=None,
        file=None,
        data=None,
        **args,
    ):
        # Carregar grafo
        graph = rdflib.Graph()
        graph.parse(source, publicID, format, location, file, data, **args)

        self.__create_hierarchy("classes")
        self._roots["classes"] = "http://www.w3.org/2002/07/owl#Thing"
        qres = graph.query(_classes_sparql)
        self.__grow_tree(graph, "classes", qres)

        self.__create_hierarchy("object_properties")
        self._roots[
            "object_properties"
        ] = "http://www.w3.org/2002/07/owl#topObjectProperty"
        qres = graph.query(_objects_sparql)
        self.__grow_tree(graph, "object_properties", qres)

        self.__create_hierarchy("data_properties")
        self._roots[
            "data_properties"
        ] = "http://www.w3.org/2002/07/owl#topDataProperty"
        qres = graph.query(_data_sparql)
        self.__grow_tree(graph, "data_properties", qres)

    def __get_max_depth(self, hierarchy_name, root):
        tree = self._trees[hierarchy_name]
        if root not in tree:
            return 0
        else:
            # Compute the depth of each subtree and use the larger one
            max_depth = 0
            for child in tree[root].children:
                max_depth = max(
                    max_depth, self.__get_max_depth(hierarchy_name, child)
                )
            return max_depth + 1

    def get_max_depth(self, hierarchy_name, node):
        if hierarchy_name in self._trees:
            # Computes the depth of node if it has not been calculated
            if hierarchy_name not in self._max_depth:
                self._max_depth[hierarchy_name] = self.__get_max_depth(
                    hierarchy_name, node
                )
            return self._max_depth[hierarchy_name]
        else:
            print("No hierarchy with that name has been created.")

    def __create_hierarchy(self, hierarchy_name):
        if hierarchy_name not in self._trees:
            self._trees[hierarchy_name] = dict()
            self._trees_names.append(hierarchy_name)
        else:
            print("A hierarchy with that name has already been created.")

    def __add_node(self, graph, hierarchy_name, node):
        if hierarchy_name in self._trees:
            # Add / Update node in the tree
            if node.data not in self._trees[hierarchy_name]:
                self._trees[hierarchy_name][node.data] = node
            else:
                current_node = self._trees[hierarchy_name][node.data]
                current_node.parent = node.parent
                if node.domains:
                    current_node.add_domain(node.domains[0])
                if node.ranges:
                    current_node.add_range(node.ranges[0])

            # Add / Update parent node in the tree
            if node.parent not in self._trees[hierarchy_name]:
                parent_node = Node(node.parent)
                parent_node.add_child(node.data)
                if "properties" in hierarchy_name:
                    if node.parent in self.properties_text:
                        parent_node.name = self.properties_text[node.parent]
                else:
                    names = _get_rdfs_label(graph, node.parent, self.lang)
                    if names:
                        parent_node.name = names[0]

                self._trees[hierarchy_name][node.parent] = parent_node

            else:
                parent_node = self._trees[hierarchy_name][node.parent]
                parent_node.add_child(node.data)
        else:
            print("No hierarchy with that name has been created.")

    def get_tree(self, hierarchy_name):
        if hierarchy_name in self._trees:
            return self._trees[hierarchy_name]
        else:
            print("No hierarchy with that name has been created.")

    def replace_tree(self, hierarchy_name, tree):
        if hierarchy_name in self._trees:
            self._trees[hierarchy_name] = tree
        else:
            print("No hierarchy with that name has been created.")

    def get_root(self, hierarchy_name):
        if hierarchy_name in self._roots:
            return self._roots[hierarchy_name]
        else:
            print("No hierarchy with that name has been created.")

    @property
    def roots(self):
        return self._roots

    @property
    def trees_names(self):
        return self._trees_names

    @property
    def trees(self):
        return self._trees
