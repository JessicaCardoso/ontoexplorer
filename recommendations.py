from rdflib import URIRef, RDFS
from rdflib import Graph
import random
import pickle
import configparser
import pathlib
import os
import sys
from unidecode import unidecode
from gensim.models import KeyedVectors

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
        self.order_set = settings.get("order_set")
        self.size = settings.getint("number_of_recommendations")
        self.text = settings.get("rec_text")
        self.suggestion_text = settings.get("suggestion_text")
        model_path = settings.get("model_path")
        if model_path and self.order=="semantic":
            self.similarity_threshold = settings.getfloat(
                "similarity_threshold"
            )
            self.embeddings = KeyedVectors.load_word2vec_format(
                model_path, binary=False, unicode_errors="ignore"
            )

    def _order_and_filter_by_similarity(self, source, targets):
        # calcular a similaridade entre os embeddings da palavra a ser
        # substituída com as candidatas.
        distances = []
        source_text = unidecode(source.name.lower()).split()
        e1 = [i if i in self.embeddings else "unk" for i in source_text]
        for node in targets:
            target_text = unidecode(node.name.lower()).split()
            e2 = [i if i in self.embeddings else "unk" for i in target_text]
            distances.append(self.embeddings.n_similarity(e1, e2))

        # Ordena do maior para o menor com base na similaridade
        suggestions = [
            targets[index]
            for index, distance in sorted(
                enumerate(distances), key=lambda x: x[1], reverse=True
            )
            if distance >= self.similarity_threshold
        ]
        return suggestions

    def _get_ascedent(self, level, node, key_tree, root):
        if level == 0:
            return node
        if root == node.data:
            return node
        return self._get_ascedent(
            level + 1, self.trees[key_tree][node.parent], key_tree, root
        )

    def _get_reference_node(self, node, key_tree, root):
        if self.family_position < 0:
            ref_node = self._get_ascedent(
                self.family_position, node, key_tree, root
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

    def _add_related_properties(
        self, class_uri, node_ref, node_list, related, list_ref="domain"
    ):
        node_list_ref = {
            "domain": node_ref.domains,
            "range": node_ref.ranges,
        }

        if class_uri:
            if class_uri in node_list_ref[list_ref]:
                related.append(node_ref)
            else:
                ancestor = self._has_ancestor_in(
                    class_uri, node_list_ref[list_ref]
                )
                if ancestor:
                    related.append(node_ref)
        else:
            check_domain = self._has_intersection(
                node_list_ref[list_ref], node_list_ref[list_ref]
            )
            if check_domain:
                related.append(node_ref)

    def _add_related_classes(
        self, class_uri, node_ref, related, list_ref="domain"
    ):
        node_list_ref = {
            "domain": node_ref.domains,
            "range": node_ref.ranges,
        }
        # Obter nós relacionados a classe
        if class_uri in node_list_ref[list_ref]:
            nodes = self._search_nodes(
                class_uri, "classes", self.roots["classes"]
            )
            for node in nodes:
                if node.data in node_list_ref[list_ref]:
                    related.append(node)
        else:
            ancestor = self._has_ancestor_in(
                class_uri, node_list_ref[list_ref]
            )
            if ancestor:
                # obter relacionados ao nó class_uri que sejam descendentes de ancestor
                nodes = self._search_nodes(class_uri, "classes", ancestor)
                for node in nodes:
                    if node.data != ancestor:
                        related.append(node)

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
                    # Obter propriedades relacionadas com base no domain
                    self._add_related_properties(
                        domain_uri, node, nodes_domains, related, "domain"
                    )
                if (
                    node not in related
                    and (self.filter_by == "range" or self.filter_by == "both")
                    and (node.ranges and prop_tree != "data_properties")
                ):
                    # Obter propriedades relacionadas com base no range
                    self._add_related_properties(
                        range_uri, node, nodes_ranges, related, "range"
                    )

            if self.order_set == "property" or self.order_set == "all":
                if self.order == "random":
                    random.shuffle(related)
                elif self.order == "semantic":
                    related = self._order_and_filter_by_similarity(
                        self.trees[prop_tree][node_key], related
                    )

        return related

    def _get_related_classes(self, node_key, domain_uri=None, range_uri=None):
        node = None
        related = []
        if node_key in self.trees["object_properties"]:
            node = self.trees["object_properties"][node_key]
            prop_tree = "object_properties"
        elif node_key in self.trees["data_properties"]:
            node = self.trees["data_properties"][node_key]
            prop_tree = "data_properties"
        if node and node not in related:
            if (
                self.filter_by == "domain" or self.filter_by == "both"
            ) and node.domains:
                # Obter classes relacionadas com base no domain
                self._add_related_classes(domain_uri, node, related, "domain")
            if prop_tree != "data_properties":
                if (
                    self.filter_by == "range" or self.filter_by == "both"
                ) and node.ranges:
                    # Obter classes relacionadas com base no range
                    self._add_related_classes(
                        range_uri, node, related, "range"
                    )

            if self.order_set == "class" or self.order_set == "all":
                if self.order == "random":
                    random.shuffle(related)
                elif self.order == "semantic":
                    if domain_uri:
                        class_node = self.trees["classes"][domain_uri]
                    if range_uri:
                        class_node = self.trees["classes"][range_uri]
                    related = self._order_and_filter_by_similarity(
                        class_node, related
                    )

        return related

    # def _get_entities(self, question_triples):
    #     question_triples.sort(key=lambda x: x[1])
    #     entities = dict()
    #     subj_ref = {}
    #     prop_ref = {}
    #     for subj, pred, obj in question_triples:
    #         if pred == "has_value":
    #             entities[subj] = False
    #             if obj in self.trees["classes"]:
    #                 entities[obj] = True
    #                 if subj in subj_ref:
    #                     subj_ref[subj].append(obj)
    #                 else:
    #                     subj_ref[subj] = [obj]
    #             else:
    #                 entities[obj] = False
    #         else:
    #             if obj in subj_ref:
    #                 for value in subj_ref[obj]:
    #                     prop_ref[value] = pred
    #             # Subject
    #             if subj not in entities:
    #                 entities[subj] = True
    #             # Object
    #             if obj not in entities:
    #                 entities[obj] = True
    #             # Predicate
    #             if entities[obj]:
    #                 entities[pred] = True
    #             else:
    #                 entities[pred] = False
    #     return prop_ref, entities

    def entities_that_can_be_exchanged(self, question_triples):
        can_be_exchanged = {}
        prop_ref = {}
        class_ref = {}

        entities_with_values = 0
        # Caso 1, se houver has_value
        for first, middle, last in question_triples:
            if middle == "has_value":
                # A classe da direita não pode ser trocada
                can_be_exchanged[first] = False
                entities_with_values += 1
                # Se o last estiver nas classes da ontologia, pode ser trocado
                if last in self.trees["classes"]:
                    can_be_exchanged[last] = True
                    # Mais de um elemento pode estar referenciando o last
                    if first in class_ref:
                        class_ref[first].append(last)
                    else:
                        class_ref[first] = [last]
                # Se for uma URI fora da ontologia, não há como trocar.
                else:
                    can_be_exchanged[last] = False

        # Caso 2, todas as entidades tem valores
        if entities_with_values == len(question_triples):
            for first, _, last in question_triples:
                can_be_exchanged[first] = True
                can_be_exchanged[last] = False
            

        # Caso 3, desconsiderar as triplas com has_value
        for first, middle, last in question_triples:
            if middle != "has_value":
                # Se o último elemento da tripla era o sujeito da classe de troca, 
                # então obtemos a sua relação
                if last in class_ref:
                    for value in class_ref[last]:
                        prop_ref[value] = middle
                # Preencher as entidades faltantes
                # Subject
                if first not in can_be_exchanged:
                    can_be_exchanged[first] = True
                # Object
                if last not in can_be_exchanged:
                    can_be_exchanged[last] = True
                # Predicate
                if can_be_exchanged[last]:
                    can_be_exchanged[middle] = True
                else:
                    can_be_exchanged[middle] = False
            
        return prop_ref, can_be_exchanged


    def get_recommendations(self, question_triples, nlg=None):
        # nlg = nlg[0]
        recommendations = []
        prop_ref, entities = self.entities_that_can_be_exchanged(question_triples)
        verified_entities = []

        for subj, pred, obj in question_triples:
            if pred == "has_value":
                if entities[obj] and obj not in verified_entities:
                    verified_entities.append(obj)
                    prop = prop_ref[obj]
                    # uri = self.trees["classes"][obj].data
                    if subj in self.trees["classes"]:
                        # name = self.trees["classes"][subj].name
                        for rec in self._get_related_classes(
                            prop, range_uri=obj
                        ):
                            recommendations.append(self.text.format(rec.name))
            else:
                if (
                    entities[obj]
                    and entities[pred]
                    and obj not in verified_entities
                ):
                    verified_entities.append(obj)
                    if pred in self.trees["object_properties"]:
                        # name = self.trees["object_properties"][pred].name
                        for rec in self._get_related_properties(
                            pred,
                            "object_properties",
                            domain_uri=subj,
                            range_uri=obj,
                        ):
                            recommendations.append(
                                self.text.format(rec.name)
                            )
                    else:
                        if pred in self.trees["data_properties"]:
                            # name = self.trees["data_properties"][pred].name
                            for rec in self._get_related_properties(
                                pred, "data_properties", domain_uri=subj
                            ):
                                recommendations.append(
                                    self.text.format(rec.name)
                                )
                if entities[subj] and subj not in verified_entities:
                    verified_entities.append(subj)
                    if subj in self.trees["classes"]:
                        # name = self.trees["classes"][subj].name
                        for rec in self._get_related_classes(pred, subj):
                            recommendations.append(
                                self.text.format(rec.name)
                            )

        return self.suggestion_text, recommendations[: self.size]
