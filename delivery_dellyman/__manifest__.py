{
    "name": "Dellyman Delivery",
    "summary": """Dellyman Delivery""",
    "description": """
        Dellyman Logistics Integration
    """,
    "author": "Matt O'Bell",
    "website": "http://www.yourcompany.com",
    "category": "Uncategorized",
    "version": "11.0.1.0.0",
    "depends": ["base", "sale_stock", "delivery", "base_geolocalize"],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "data/delivery_data.xml",
        "views/delivery_carrier.xml",
        "views/views.xml",
    ],
    "external_dependencies": {
        "python": ["geopy"],
    },
}
