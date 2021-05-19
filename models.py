"""
This file defines the database models
"""

from .common import db, Field
from pydal.validators import *

db.define_table(
    "product",
    Field("name"),
    Field("price", "decimal(9,2)", requires=IS_DECIMAL_IN_RANGE(0, 9999)),
)


db.define_table("customer", Field("name"), Field("city"), Field("state"))

db.define_table(
    "order",
    Field(
        "customer",
        "reference customer",
        requires=IS_IN_DB(db, "customer.id", "%(name)s", zero=".."),
    ),
    Field("total", "decimal(11,2)"),
)

db.define_table(
    "order_line",
    Field(
        "order",
        "reference order",
        requires=IS_IN_DB(db, "order.id", "%(id)s", zero=".."),
    ),
    Field(
        "product",
        "reference product",
        requires=IS_IN_DB(db, "product.id", "%(name)s", zero=".."),
    ),
    Field("price", "decimal(9,2)"),
    Field("quantity", "decimal(7,2)"),
)


def order_line_before_update(set, fields):
    if fields:
        quantity = fields.get("quantity")
        product_id = fields.get("product")
        product = db.product(product_id)
        if quantity and product and product.price:
            price = quantity * product.price
        else:
            price = 0

        fields["price"] = price


def order_line_after_update(fields, key_id):
    order_id = fields.get("order")

    #  get order total
    total = (
        db(db.order_line.order == order_id)
        .select(db.order_line.price.sum())
        .first()[db.order_line.price.sum()]
    )

    order = db.order(order_id)
    order.update_record(total=total)


def order_line_before_delete(s):
    for row in db(s.query).select():
        #  update the order total not including this record
        total = (
            db((db.order_line.order == row.order) & (db.order_line.id != row.id))
            .select(db.order_line.price.sum())
            .first()[db.order_line.price.sum()]
        )
        order = db.order(row.order)
        order.update_record(total=total)


db.order_line._before_insert.append(lambda f: order_line_before_update("", f))
db.order_line._before_update.append(lambda s, f: order_line_before_update(s, f))
db.order_line._after_insert.append(lambda f, i: order_line_after_update(f, i))
db.order_line._after_update.append(lambda s, f: order_line_after_update(f, 0))
db.order_line._before_delete.append(lambda s: order_line_before_delete(s))

db.commit()
