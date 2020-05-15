from rdflib import URIRef, RDFS
from rdflib import Graph
import random
import pickle
import configparser
import pathlib
import os
import sys


_ROOT = pathlib.Path(__file__).parent.absolute()


class Recommendation:
    def __init__(self):
        onto_trees = pickle.load(
            open(os.path.join(_ROOT, "ontology_trees.pkl"), "rb")
        )

        config = configparser.ConfigParser(delimiters="=")
        config.read(os.path.join(_ROOT, "recommendation.ini"))
        settings = config["DEFAULT"]

        ontology_path = os.path.join(_ROOT, settings["ontology_filename"])

        self.graph = Graph()
        self.graph.parse(ontology_path, format=settings["ontology_format"])

        self.trees = onto_trees.trees
        self.roots = onto_trees.roots

        self.depth = settings.getint("depth")
        self.family_position = settings.getint("family_position")
        self.filter_by = settings.get("filter_by")
        self.order = settings.get("order")
        self.size = settings.getint("number_of_recommendations")

    def _get_ascedent(self, level, node, key_tree, root):
        if level == 0:
            return node
        if root == node.data:
            return node
        return self._get_ascedent(
            level + 1, self.trees[key_tree][node.parent], key_tree, root
        )

    def _get_descendent(self, level, node, key_tree):
        if level == 0:
            return node
        if node.is_leaf:
            return node
        return self._get_descendent(
            level - 1, self.trees[key_tree][node.parent], key_tree
        )

    def _get_reference_node(self, node, key_tree, root):
        if self.family_position < 0:
            ref_node = self._get_ascedent(
                self.family_position, node, key_tree, root
            )
        elif self.family_position > 0:
            ref_node = self._get_descendent(
                self.family_position, node, key_tree
            )
        else:
            ref_node = node
        return ref_node

    def _get_given_level(self, nodes, ignore_node, root, level, key_tree):
        if root.data not in self.trees[key_tree]:
            return root
        if level == 1:
            if root != ignore_node:
                nodes.append(root)
        elif level > 1:
            for child_key in root.children:
                self._get_given_level(
                    nodes,
                    ignore_node,
                    self.trees[key_tree][child_key],
                    level - 1,
                    key_tree,
                )

    def _get_level_order(self, ignore_node, node, level, key_tree):
        nodes = []
        ignore_node = ignore_node
        for i in range(1, level + 1):
            self._get_given_level(nodes, ignore_node, node, i, key_tree)
        return nodes

    def _search_nodes(self, node_key, key_tree, root):
        node = self.trees[key_tree][node_key]
        ref_node = self._get_reference_node(node, key_tree, root)
        nodes = self._get_level_order(node, ref_node, self.depth, key_tree)
        return nodes

    def _is_descendent_of(self, classe, super_classe):
        for subject in self.graph.subjects(
            predicate=RDFS.subClassOf, object=URIRef(super_classe)
        ):
            subject = str(subject)
            if subject == classe or self._is_descendent_of(classe, subject):
                return True
        return False

    def _has_ancestor_in(self, ref, candidates):
        has_acenstor = False
        for ancestor in candidates:
            if self._is_descendent_of(ref, ancestor):
                has_acenstor = True
                break
        if has_acenstor:
            return ancestor
        else:
            return None

    def _has_intersection(self, group_1, group_2):
        has_intersection = True
        for elm in group_1:
            if elm not in group_2:
                has_intersection = False
                break
        return has_intersection

    def _get_related_properties(
        self,
        node_key,
        prop_tree="object_properties",
        domain_uri=None,
        range_uri=None,
    ):
        related = []
        if node_key in self.trees[prop_tree]:
            nodes = self._search_nodes(
                node_key, prop_tree, self.roots[prop_tree]
            )
            nodes_domains = self.trees[prop_tree][node_key].domains
            nodes_ranges = self.trees[prop_tree][node_key].ranges
            for node in nodes:
                if (
                    node not in related
                    and (
                        self.filter_by == "domain"
                        or self.filter_by == "both"
                        or prop_tree == "data_properties"
                    )
                    and node.domains
                ):
                    if domain_uri:
                        if domain_uri in node.domains:
                            related.append(node)
                        else:
                            ancestor = self._has_ancestor_in(
                                domain_uri, node.domains
                            )
                            if ancestor:
                                related.append(node)
                    else:
                        check_domain = self._has_intersection(
                            nodes_domains, node.domains
                        )
                        if check_domain:
                            related.append(node)

                if (
                    node not in related
                    and (self.filter_by == "range" or self.filter_by == "both")
                    and (node.ranges and prop_tree != "data_properties")
                ):
                    if range_uri:
                        if range_uri in node.ranges:
                            related.append(node)
                        else:
                            ancestor = self._has_ancestor_in(
                                range_uri, node.ranges
                            )
                            if ancestor:
                                related.append(node)
                    else:
                        check_range = self._has_intersection(
                            nodes_ranges, node.ranges
                        )
                        if check_range:
                            related.append(node)
            if self.order == "random":
                random.shuffle(related)
        return related[: self.size]

    def _add_related_classes(
        self, ignore_uri, node_ref, related, list_ref="domain"
    ):
        node_list_ref = {
            "domain": node_ref.domains,
            "range": node_ref.ranges,
        }
        for uri in node_list_ref[list_ref]:
            if uri != ignore_uri:
                related.append(self.trees["classes"][uri])

    def _get_related_classes(self, node_key, domain_uri=None, range_uri=None):
        node = None
        related = []
        if node_key in self.trees["object_properties"]:
            node = self.trees["object_properties"][node_key]
            prop_tree = "object_properties"
        elif node_key in self.trees["data_properties"]:
            node = self.trees["data_properties"][node_key]
            prop_tree = "data_properties"
        if node:
            if (
                node not in related
                and (
                    self.filter_by == "domain"
                    or self.filter_by == "both"
                    or prop_tree == "data_properties"
                )
                and node.domains
            ):
                if domain_uri in node.domains:
                    self._add_related_classes(
                        domain_uri, node, related, "domain"
                    )
                else:
                    ancestor = self._has_ancestor_in(domain_uri, node.domains)
                    if ancestor:
                        self._add_related_classes(
                            ancestor, node, related, "domain"
                        )
                        # obter relacionados ao nó domain_uri que sejam descendentes de ancestor
                        nodes = self._search_nodes(
                            domain_uri, "classes", ancestor
                        )
                        for node in nodes:
                            if node.data != ancestor:
                                related.append(node)
            if (
                node not in related
                and (self.filter_by == "range" or self.filter_by == "both")
                and (node.ranges and prop_tree != "data_properties")
            ):
                if range_uri in node.ranges:
                    self._add_related_classes(
                        range_uri, node, related, "range"
                    )
                else:
                    ancestor = self._has_ancestor_in(range_uri, node.ranges)
                    if ancestor:
                        self._add_related_classes(
                            ancestor, node, related, "range"
                        )
                        # obter relacionados ao nó range_uri que sejam descendentes de ancestor
                        nodes = self._search_nodes(
                            range_uri, "classes", ancestor
                        )
                        for node in nodes:
                            if node.data != ancestor:
                                related.append(node)
            if self.order == "random":
                random.shuffle(related)
        return related[: self.size]

    def _get_entities(self, question_triples):
        question_triples.sort(key=lambda x: x[1])
        entities = dict()
        subj_ref = {}
        prop_ref = {}
        for subj, pred, obj in question_triples:
            if pred == "has_value":
                entities[subj] = False
                if obj in self.trees["classes"]:
                    entities[obj] = True
                    if subj in subj_ref:
                        subj_ref[subj].append(obj)
                    else:
                        subj_ref[subj] = [obj]
                else:
                    entities[obj] = False
            else:
                if obj in subj_ref:
                    for value in subj_ref[obj]:
                        prop_ref[value] = pred
                # Subject
                if subj not in entities:
                    entities[subj] = True
                # Object
                if obj not in entities:
                    entities[obj] = True
                # Predicate
                if entities[obj]:
                    entities[pred] = True
                else:
                    entities[pred] = False
        return prop_ref, entities

    def get_recommendations(self, question_triples):
        recommendations = []
        prop_ref, entities = self._get_entities(question_triples)
        verified_entities = []
        for subj, pred, obj in question_triples:
            if pred == "has_value":
                if entities[obj] and obj not in verified_entities:
                    verified_entities.append(obj)
                    prop = prop_ref[obj]
                    # name = self.trees["classes"][obj].name
                    name = self.trees["classes"][subj].name
                    for rec in self._get_related_classes(prop, range_uri=obj):
                        recommendations.append(f"[{name}]: [{rec.name}]")
            else:
                if (
                    entities[obj]
                    and entities[pred]
                    and obj not in verified_entities
                ):
                    verified_entities.append(obj)
                    if pred in self.trees["object_properties"]:
                        name = self.trees["object_properties"][pred].name
                        for rec in self._get_related_properties(
                            pred,
                            "object_properties",
                            domain_uri=subj,
                            range_uri=obj,
                        ):
                            recommendations.append(f"[{name}] -> [{rec.name}]")
                    else:
                        name = self.trees["data_properties"][pred].name
                        for rec in self._get_related_properties(
                            pred, "data_properties", domain_uri=subj
                        ):
                            recommendations.append(f"[{name}] -> [{rec.name}]")
                if entities[subj] and subj not in verified_entities:
                    verified_entities.append(subj)
                    name = self.trees["classes"][subj].name
                    for rec in self._get_related_classes(pred, subj):
                        recommendations.append(f"[{name}] -> [{rec.name}]")

        if self.order == "random":
          random.shuffle(recommendations)

        return recommendations[: self.size]
