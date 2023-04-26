# search module for generic elasticsearch index and query logic
# requires setup:
# - elasticsearch is initialized in app factory function
# - model attribute `__searchable__`

from flask import current_app


# if add an entry with an existing id, then Elasticsearch replaces the
# old entry with the new one, so add_to_index() can be used for both
# insert and update index documents
def add_to_index(index, model):
    # first check if elasticsearch is loaded to current app
    if not current_app.elasticsearch:
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
        current_app.elasticsearch.index(index=index, id=model.id, document=payload)


def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, id=model.id)


# use 'multi-match' query mode against all fields (['*'])
# also support pagination
def query_index(index, query, page, per_page):
    if not current_app.elasticsearch:
        return
    search = current_app.elasticsearch.search(
        index=index,
        query={'multi_match': {'query': query, 'fields': ['*']}},
        from_=(page - 1) * per_page,
        size=per_page
    )
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']