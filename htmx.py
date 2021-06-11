import base64
import codecs
import json
import pickle
from functools import reduce

from yatl import DIV, INPUT, SCRIPT

from .common import session, db, auth
from py4web import action, request, URL


def autocomplete_widget(field, values_dict):
    control = DIV()
    if "_table" in dir(field):
        tablename = field._table
    else:
        tablename = "no_table"

    value = values_dict[field.name] if field.name in values_dict else ""
    #  build the div-hidden input field to hold the value
    hidden_input = INPUT(
        _type="text",
        _id="%s_%s" % (tablename, field.name),
        _name=field.name,
        _value=value,
    )
    hidden_div = DIV(hidden_input, _style="display: none;")
    control.append(hidden_div)

    #  build the input field to accept the text

    #  set the htmx attributes
    attrs = {
        "_hx-post": URL("htmx/autocomplete"),
        "_hx-trigger": "keyup changed delay:500ms",
        "_hx-target": "#%s_%s_autocomplete_results" % (tablename, field.name),
        "_hx-indicator": ".htmx-indicator",
        "_hx-vals": '{"tablename": "%(tablename)s", "fieldname": "%(fieldname)s"}'
        % {"tablename": str(tablename), "fieldname": field.name},
    }
    search_value = None
    if value and field.requires:
        row = (
            db(db[field.requires.ktable][field.requires.kfield] == value)
            .select()
            .first()
        )
        if row:
            search_value = field.requires.label % row

    control.append(
        INPUT(
            _type="text",
            _id="%s_%s_search" % (tablename, field.name),
            _name="%s_%s_search" % (tablename, field.name),
            _value=search_value,
            _class="input",
            _placeholder="..",
            _title="Enter search string",
            _autocomplete="off",
            **attrs,
        )
    )

    control.append(DIV(_id="%s_%s_autocomplete_results" % (tablename, field.name)))

    control.append(
        SCRIPT(
            """
    htmx.onLoad(function(elt) {
        document.querySelector('#%(table)s_%(field)s_search').onkeydown = check_%(table)s_%(field)s_down_key;
        \n
        function check_%(table)s_%(field)s_down_key(e) {
            if (e.keyCode == '40') {
                document.querySelector('#%(table)s_%(field)s_autocomplete').focus();
                document.querySelector('#%(table)s_%(field)s_autocomplete').selectedIndex = 0;
            }
        }
    })
        """
            % {
                "table": tablename,
                "field": field.name,
            }
        )
    )

    return control


@action(
    "htmx/autocomplete",
    method=["GET", "POST"],
)
@action.uses(
    session,
    db,
    "htmx/autocomplete.html",
)
def autocomplete():
    tablename = request.params.tablename
    fieldname = request.params.fieldname
    autocomplete_query = request.params.query

    field = db[tablename][fieldname]
    data = []

    fk_table = None

    if field and field.requires:
        fk_table = field.requires.ktable
        fk_field = field.requires.kfield

        queries = []
        if "_autocomplete_search_fields" in dir(field):
            for sf in field._autocomplete_search_fields:
                queries.append(
                    db[fk_table][sf].contains(
                        request.params[f"{tablename}_{fieldname}_search"]
                    )
                )
            query = reduce(lambda a, b: (a | b), queries)
        else:
            for f in db[fk_table]:
                if f.type in ["string", "text"]:
                    queries.append(
                        db[fk_table][f.name].contains(
                            request.params[f"{tablename}_{fieldname}_search"]
                        )
                    )

            query = reduce(lambda a, b: (a | b), queries)

        if len(queries) == 0:
            queries = [db[fk_table].id > 0]
            query = reduce(lambda a, b: (a & b), queries)

        if autocomplete_query:
            query = reduce(lambda a, b: (a & b), [autocomplete_query, query])
        data = db(query).select(orderby=field.requires.orderby)

    return dict(
        data=data,
        tablename=tablename,
        fieldname=fieldname,
        fk_table=fk_table,
        data_label=field.requires.label,
    )


class NewHtmxAutocompleteWidget:
    def __init__(self, simple_query=None, url=None, **attrs):
        self.query = simple_query
        self.url = url if url else URL("htmx/autocomplete")
        self.attrs = attrs

        self.attrs.pop("simple_query", None)
        self.attrs.pop("url", None)

    def make(self, field, value, error, title, placeholder="", readonly=False):
        #  TODO: handle readonly parameter
        control = DIV()
        if "_table" in dir(field):
            tablename = field._table
        else:
            tablename = "no_table"

        #  build the div-hidden input field to hold the value
        hidden_input = INPUT(
            _type="text",
            _id="%s_%s" % (tablename, field.name),
            _name=field.name,
            _value=value,
        )
        hidden_div = DIV(hidden_input, _style="display: none;")
        control.append(hidden_div)

        #  build the input field to accept the text

        #  set the htmx attributes

        values = {
            "tablename": str(tablename),
            "fieldname": field.name,
            "query": str(self.query) if self.query else "",
            **self.attrs,
        }
        attrs = {
            "_hx-post": self.url,
            "_hx-trigger": "keyup changed delay:500ms",
            "_hx-target": "#%s_%s_autocomplete_results" % (tablename, field.name),
            "_hx-indicator": ".htmx-indicator",
            "_hx-vals": json.dumps(values),
        }
        search_value = None
        if value and field.requires:
            row = (
                db(db[field.requires.ktable][field.requires.kfield] == value)
                .select()
                .first()
            )
            if row:
                search_value = field.requires.label % row

        control.append(
            INPUT(
                _type="text",
                _id="%s_%s_search" % (tablename, field.name),
                _name="%s_%s_search" % (tablename, field.name),
                _value=search_value,
                _class="input",
                _placeholder=placeholder if placeholder and placeholder != "" else "..",
                _title=title,
                _autocomplete="off",
                **attrs,
            )
        )

        control.append(DIV(_id="%s_%s_autocomplete_results" % (tablename, field.name)))

        control.append(
            SCRIPT(
                """
        htmx.onLoad(function(elt) {
            document.querySelector('#%(table)s_%(field)s_search').onkeydown = check_%(table)s_%(field)s_down_key;
            \n
            function check_%(table)s_%(field)s_down_key(e) {
                if (e.keyCode == '40') {
                    document.querySelector('#%(table)s_%(field)s_autocomplete').focus();
                    document.querySelector('#%(table)s_%(field)s_autocomplete').selectedIndex = 0;
                }
            }
        })
            """
                % {
                    "table": tablename,
                    "field": field.name,
                }
            )
        )

        return control
