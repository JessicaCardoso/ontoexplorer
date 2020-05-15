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

| **Params**                | **Default**       | **Description**                                                                                          |
| ------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------- |
| family_position           | -2                | Nível em relação ao <mark>nó de referência</mark>, pode assumir valores negativos e positivos.           |
| filter_by                 | both              | Se a indicação do nó deve ser baseada no _range_, _domain_ ou ambos.                                     |
| depth                     | 3                 | Profundidade da busca na árvore a partir da *family_position*, pode assumir apenas valores positivo.     |
| order                     | random            | A forma como as sugestões serão apresentadas, se nenhum parâmetro for passado retorna na ordem da busca. |
| number_of_recommendations | 5                 | Quantidade máxima de recomendações, deve ser um número maior do que zero.                                |
| ontology_filename         | movieontology.ttl | Nome do arquivo da ontologia que se encontra no mesmo nível de *recommendation.py*.                      |
| ontology_format           | ttl               | formato da ontologia, formato definido de acordo com os formatos da rdflib.                              |

> nó de referência, é o nó que desejamos substituir por outro

### Nós relacionados:

A fórmula a seguir representa o *grau familiar máximo* do nó de referência a ser considerado.

<!-- ![equation](https://latex.codecogs.com/gif.latex?root_{ref}&space;=&space;\left\{\begin{matrix}&space;node_{ref}&space;&plus;&space;fp&space;&&space;\text{if&space;$fp>0$,}&space;\\&space;node_{ref}&space;-&space;fp&space;&&space;\text{if&space;$fp<0$,}&space;\\&space;node_{ref}&space;&&space;\text{otherwise}&space;\end{matrix}\right.) -->
![equation](misc/root_ref.gif)


Onde ![fp](https://render.githubusercontent.com/render/math?math=fp) é a *family_position*, ![node_ref](https://render.githubusercontent.com/render/math?math=node_{ref}) é o nível do nó de referência e ![root_ref](https://render.githubusercontent.com/render/math?math=root_{ref}) é o grau familiar máximo calculado. Por exemplo, na árvore de classes, dado o nó de referência *Actor*, se o ![fp](https://render.githubusercontent.com/render/math?math=fp) for definido como -1, o ![root_ref](https://render.githubusercontent.com/render/math?math=root_{ref}) apontaria para o nó *Person*.

Outro parâmetro importante é a profundidade da consulta na árvore que é definida pela variável _depth_ que pode assumir <mark>apenas valores positivos</mark>. Suponha que o ![node_ref](https://render.githubusercontent.com/render/math?math=node_{ref}) seja o nó *Person*, se a profundidade definida for 1, então todos os filhos de *Person* podem ser sugeridos.

Também podemos filtrar os nós a serem sugeridos com base em seu domínio e  alcance, na tabela a seguir temos alguns exemplos de nós da árvore de propriedade com seus respectivos *domains* e *ranges*, para o próximo exemplo vamos considerar o ![fp=1](https://render.githubusercontent.com/render/math?math=fp=1) e a ![fp=1](https://render.githubusercontent.com/render/math?math=depth=2).

| **Object Property** | **Domain**            | **Range**      |
| ------------------- | --------------------- | -------------- |
| belongsToGenre      | Movie/TVSeries        | Genre          |
| hasActress          | Movie/TVSeries        | Actress        |
| hasActor            | Movie/TVSeries        | Actor          |
| isAwardedWith       | Movie/TVSeries/Person | Award          |
| wrote               | Writer                | Movie/TVSeries |

Dada a propriedade *wrote* se quisermos delimitar pelo *Range*, teremos zero sugestões, pois não existe outra propriedade com o *Range* de *wrote* nesta tabela. Entretanto se filtramos a propriedade pelo *Domain* podemos sugerir a propriedade *isAwardedWith*, pois *Writer* é descendente de *Person* como podemos ver na imagem _Classes Tree_. 

Caso a propriedade de referência seja *belongsToGenre* e filtremos pelo *Domain* teremos como sugestão *hasActress*, *hasActor* e *isAwardedWith* pois compartilham domínios em comum com *belongsToGenre*.

### Exemplo:

<p align="center">
<img src="misc/ex1.png" height=200/>
</p>

```python
from recommendations import Recommendation

# Qual o gênero do filme Avatar?
rec = Recommendation()

question_triples =  [
    ("http://www.movieontology.org/2009/10/01/movieontology.owl#Movie", "has_value", "Avatar"),
     ("http://www.movieontology.org/2009/10/01/movieontology.owl#Movie", "http://www.movieontology.org/2009/10/01/movieontology.owl#belongsToGenre", "http://www.movieontology.org/2009/10/01/movieontology.owl#Genre")
]

rec.get_recommendations(question_triples)
#['[Gênero(s)] -> [Diretor(es)]', '[Gênero(s)] -> [Companhia(s) de produção]', '[Gênero(s)] -> [Roteirista(s)]', '[Gênero(s)] -> [Editor(es)]', '[Gênero(s)] -> [Indicação/Indicações]']
```
