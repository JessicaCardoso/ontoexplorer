# ontoexplorer

![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

## Árvores da ontologia

Este repositório contém o código fonte das recomendações de classes e propriedades da ontologia utilizada pelo [OntoIQA-Bot](https://github.com/JessicaSousa/OntoIQA-Bot). Para a construção das árvores de ontologias são necessários os seguintes requisitos: 

**Requisitos:**

- Arquivo contendo a  ontologia (ex.: [movieontology.ttl](movieontology.ttl))
- Arquivo contendo os labels das propriedades (ex.: [properties_labels.ini](properties_labels.ini))

> Obs: É necessária a instalação das bibliotecas do Pipefile.

No notebook [onto_tree_build.ipynb](onto_tree_build.ipynb) é realizada a construção das árvores através da classe _OntologyTrees_, o arquivo da ontologia deve ser um formato aceito pela biblioteca [rdflib](https://rdflib.readthedocs.io/en/stable/).

```python
from ontotrees import OntologyTrees

onto_trees = OntologyTrees()

# Carregar o grafo da ontologia em três árvores de hierarquia (classes, propriedades de objeto e propriedades de dado)
onto_trees.load_ontology("movieontology.ttl", format="ttl")

# Nomes das árvores carregadas
onto_trees.trees_names
# >> ['classes', 'object_properties', 'data_properties']
```

Na Figura a seguir ilustramos parte das árvores carregadas pela classe _OntologyTrees_.

<img src="misc/onto_trees.png" align="center"> </img>

## Recomendação de nós

O processo de recomendação realizada na classe `Recommendation` é ajustado no arquivo de configurações [recommendation.ini](recommendation.ini). Onde:


| **Params**                	| **Default**       	| **Description**                                                                   	|
|---------------------------	|-------------------	|-----------------------------------------------------------------------------------	|
| family_position           	| -2                	| Nível em relação ao nó de referência, pode assumir valores negativos e positivos. 	|
| filter_by                 	| both              	| Se a indicação do nó deve ser baseado no _range_ ou _domain_ ou ambos.            	|
| depth                     	| 3                 	| Profundidade da busca na árvore a partir da _family_position_.                    	|
| order                     	| random            	| A forma como as sugestões serão apresentadas.                                     	|
| number_of_recommendations 	| 5                 	| Quantidade de recomendações máxima.                                               	|
| ontology_filename         	| movieontology.ttl 	| Nome do arquivo da ontologia que se encontra no mesmo de nível recommendation.py  	|
| ontology_format           	| ttl               	| formato da ontologia, formato definido de acordo com os formatos da rdflib.       	|

#### Exemplo:

```python
from recommendations import Recommendation

# Qual o gênero do filme Avatar?
rec = Recommendation()>>> question_triples =  [
    ("http://www.movieontology.org/2009/10/01/movieontology.owl#Movie", "has_value", "Avatar"),
     ("http://www.movieontology.org/2009/10/01/movieontology.owl#Movie", "http://www.movieontology.org/2009/10/01/movieontology.owl#belongsToGenre", "http://www.movieontology.org/2009/10/01/movieontology.owl#Genre")
]

rec.get_recommendations(question_triples)
#['[Gênero(s)] -> [Diretor(es)]', '[Gênero(s)] -> [Companhia(s) de produção]', '[Gênero(s)] -> [Roteirista(s)]', '[Gênero(s)] -> [Editor(es)]', '[Gênero(s)] -> [Indicação/Indicações]']
```

<img src="misc/ex1.png" height=200 align="center"/>