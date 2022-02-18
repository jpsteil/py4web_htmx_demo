import csv
from functools import reduce

from yatl.helpers import TAG

from py4web import action, URL, request
from py4web.utils.form import FormStyleBulma, FormStyleFactory
from py4web.utils.grid import (
    Grid,
    get_parent,
    GridClassStyleBulma,
    AttributesPluginHtmx,
)
from .common import (
    db,
    session,
    auth,
)
from .htmx import NewHtmxAutocompleteWidget

BUTTON = TAG.button


@action("index", method=["POST", "GET"])
@action("index/<path:path>", method=["POST", "GET"])
@action.uses(
    "index.html",
    session,
    db,
    auth,
)
def index(path=None):
    return dict()


@action("customers", method=["POST", "GET"])
@action("customers/<path:path>", method=["POST", "GET"])
@action.uses(
    "customers.html",
    session,
    db,
    auth,
)
def customers(path=None):
    grid = Grid(
        path,
        query=reduce(lambda a, b: (a & b), [db.customer.id > 0]),
        orderby=[db.customer.name],
        details=False,
        grid_class_style=GridClassStyleBulma,
        formstyle=FormStyleBulma,
    )
    parent_id = None
    if grid.action in ["details", "edit"]:
        parent_id = grid.record_id

    return dict(grid=grid, parent_id=parent_id)


@action("customer_orders", method=["POST", "GET"])
@action("customer_orders/<path:path>", method=["POST", "GET"])
@action.uses(
    "customer_orders.html",
    session,
    db,
    auth,
)
def customer_orders(path=None):
    #  set the default
    customer_id = get_parent(
        path,
        parent_field=db.order.customer,
    )
    db.order.customer.default = customer_id

    #  get order total
    total = (
        db(db.order.customer == customer_id)
        .select(db.order.total.sum())
        .first()[db.order.total.sum()]
    )

    # if path and path.split("/")[0] in ["new", "details", "edit"]:
    #    db.order_line.price.readable = False
    #    db.order_line.price.writable = False

    grid = Grid(
        path,
        fields=[db.order.id, db.order.total],
        show_id=True,
        headings=["ORDER #", "TOTAL"],
        query=reduce(
            lambda a, b: (a & b),
            [db.order.customer == customer_id],
        ),
        orderby=[db.order.id],
        auto_process=False,
        rows_per_page=5,
        grid_class_style=GridClassStyleBulma,
        formstyle=FormStyleBulma,
        create=True,
        details=True,
        editable=True,
        deletable=True,
        include_action_button_text=False,
    )

    grid.attributes_plugin = AttributesPluginHtmx("#htmx-target")
    grid.process()

    return dict(grid=grid, total=total)


@action("products", method=["POST", "GET"])
@action("products/<path:path>", method=["POST", "GET"])
@action.uses(
    "grid.html",
    session,
    db,
    auth,
)
def products(path=None):
    grid = Grid(
        path,
        query=reduce(lambda a, b: (a & b), [db.product.id > 0]),
        orderby=[db.product.name],
        details=False,
        grid_class_style=GridClassStyleBulma,
        formstyle=FormStyleBulma,
    )

    return dict(grid=grid)


@action("order_lines", method=["POST", "GET"])
@action("order_lines/<path:path>", method=["POST", "GET"])
@action.uses(
    "order_lines.html",
    session,
    db,
    auth,
)
def order_lines(path=None):
    #  set the default
    order_id = get_parent(
        path,
        parent_field=db.order_line.order,
    )
    db.order_line.order.default = order_id

    left = db.product.on(db.order_line.product == db.product.id)

    #  get order total
    total = (
        db(db.order_line.order == order_id)
        .select(db.order_line.price.sum())
        .first()[db.order_line.price.sum()]
    )

    if path and path.split("/")[0] in ["new", "details", "edit"]:
        db.order_line.price.readable = False
        db.order_line.price.writable = False

    formstyle = FormStyleFactory()
    formstyle.classes = FormStyleBulma.classes
    formstyle.class_inner_exceptions = FormStyleBulma.class_inner_exceptions
    formstyle.widgets["product"] = NewHtmxAutocompleteWidget(
        url=URL("product_autocomplete"), order_id=order_id
    )

    grid = Grid(
        path,
        fields=[
            db.product.name,
            db.order_line.quantity,
            db.product.price,
            db.order_line.price,
        ],
        headings=["PRODUCT", "QTY", "UNIT", "EXT"],
        query=reduce(
            lambda a, b: (a & b),
            [db.order_line.order == order_id],
        ),
        left=left,
        orderby=[db.order_line.id],
        auto_process=False,
        rows_per_page=5,
        grid_class_style=GridClassStyleBulma,
        formstyle=formstyle,
        details=False,
        include_action_button_text=False,
    )

    grid.attributes_plugin = AttributesPluginHtmx("#htmx-target")
    attrs = {
        "_hx-get": URL("order_lines", vars=dict(parent_id=order_id)),
        "_class": "button is-default",
    }
    grid.param.new_sidecar = BUTTON("Cancel", **attrs)
    grid.param.edit_sidecar = BUTTON("Cancel", **attrs)

    grid.process()

    return dict(grid=grid, total=total)


@action("orders", method=["POST", "GET"])
@action("orders/<path:path>", method=["POST", "GET"])
@action.uses(
    "orders.html",
    session,
    db,
    auth,
)
def orders(path=None):
    left = db.customer.on(db.order.customer == db.customer.id)

    show_id = True
    if path and path.split("/")[0] in ["details", "edit"]:
        db.order.total.readable = False
        show_id = False

    db.order.total.writable = False

    grid = Grid(
        path,
        fields=[db.order.id, db.customer.name, db.order.total],
        show_id=show_id,
        headings=["ORDER #", "CUSTOMER", "TOTAL"],
        query=reduce(lambda a, b: (a & b), [db.order.id > 0]),
        orderby=[db.order.id],
        left=left,
        grid_class_style=GridClassStyleBulma,
        details=False,
        formstyle=FormStyleBulma,
    )

    parent_id = None
    if grid.action in ["details", "edit"]:
        parent_id = grid.record_id

    return dict(grid=grid, parent_id=parent_id)


def build_beers():
    with open("/home/jim/Documents/beers.csv", "r") as f:
        for x, line in enumerate(csv.reader(f)):
            if x > 0:
                beer = line[0]
                price = line[1]

                print(beer, price)

                db.product.insert(name=beer, price=price)

    db.commit()


@action(
    "product_autocomplete",
    method=["GET", "POST"],
)
@action.uses(
    "htmx/autocomplete.html",
    session,
    db,
)
def product_autocomplete():
    tablename = request.params.tablename
    fieldname = request.params.fieldname
    order_id = request.params.order_id

    field = db[tablename][fieldname]
    data = []

    fk_table = None

    if field and field.requires:
        fk_table = field.requires.ktable
        fk_field = field.requires.kfield

        queries = []
        products_already_on_order = db(db.order_line.order == order_id)._select(
            db.order_line.product
        )
        queries.append(~db.product.id.belongs(products_already_on_order))
        queries.append(
            db.product.name.contains(request.params["order_line_product_search"])
        )
        query = reduce(lambda a, b: (a & b), queries)

        data = db(query).select(orderby=field.requires.orderby)

    return dict(
        data=data,
        tablename=tablename,
        fieldname=fieldname,
        fk_table=fk_table,
        data_label=field.requires.label,
    )
