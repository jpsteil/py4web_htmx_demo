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
    htmx.on('htmx:load', function(evt) {
        console.log('htmx loaded')
        function select_%(fk_table)s(v) {
            document.querySelector('input#%(table)s_%(field)s').value = v.value
            document.querySelector('#%(table)s_%(field)s_search').value = v.label
    
            htmx.remove(htmx.find('#%(table)s_%(field)s_autocomplete'))
        }
        document.querySelector('#%(table)s_%(field)s_search').addEventListener('focusout', (event) => {
            if (event.relatedTarget === null || event.relatedTarget.id !== '%(table)s_%(field)s_autocomplete') {
                if (htmx.find('#%(table)s_%(field)s_autocomplete') !== null) {
                    htmx.remove(htmx.find('#%(table)s_%(field)s_autocomplete'))
                }
            }
        })
        document.querySelector('#%(table)s_%(field)s_search').onkeydown = check_%(table)s_%(field)s_down_key;
    
        function check_%(table)s_%(field)s_down_key(e) {
            if (e.keyCode == '40') {
                document.querySelector('#%(table)s_%(field)s_autocomplete').focus();
                document.querySelector('#%(table)s_%(field)s_autocomplete').selectedIndex = 0;
            }
        }
        function check_%(table)s_%(field)s_enter_key(e) {
            if (e.key === 'Enter' || e.keyCode == '13') {
                var v = {
                    'value': this.value,
                    'label': document.querySelector('#%(table)s_%(field)s_autocomplete :checked').innerHTML.trim()
                }
                select_%(fk_table)s(v);
            }
        }
    })
        """
            % {
                "table": tablename,
                "field": field.name,
                "fk_table": field.requires.ktable,
                "fk_field": field.requires.kfield,
            }
        )
    )

    return control


@action(
    "htmx/autocomplete",
    method=["GET", "POST"],
)
@action.uses(
    db,
    "htmx/autocomplete.html",
)
def autocomplete():
    tablename = request.params.tablename
    fieldname = request.params.fieldname

    field = db[tablename][fieldname]
    data = []

    fk_table = None

    if field and field.requires:
        fk_table = field.requires.ktable
        fk_field = field.requires.kfield

        if "_autocomplete_search_fields" in field:
            queries = []
            for sf in field._autocomplete_search_fields:
                queries.append(
                    db[fk_table][sf].contains(
                        request.params[f"{tablename}_{fieldname}_search"]
                    )
                )
            query = reduce(lambda a, b: (a | b), queries)
        else:
            queries = [db[fk_table].id > 0]
            query = reduce(lambda a, b: (a & b), queries)

        data = db(query).select(orderby=field.requires.orderby)

    return dict(
        data=data,
        tablename=tablename,
        fieldname=fieldname,
        fk_table=fk_table,
        data_label=field.requires.label,
    )
