import csv
import os
from app import app, db, Item, Chemical

def import_items(filename):
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            item = Item(
                name=row['Name'],
                quantity=int(row['Quantity']),
                cupboard=row['Cupboard'],
                shelf=row.get('Shelf', ''),
                box=row.get('Box', ''),
                expiry_date=row.get('Expiry Date', ''),
                notes=row.get('Notes', '')
            )
            db.session.add(item)
            count += 1
        db.session.commit()
        print(f"Imported {count} items!")

def import_chemicals(filename):
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            chem = Chemical(
                name=row['Name'],
                cupboard=row['Cupboard'],
                shelf=row.get('Shelf', ''),
                box=row.get('Box', ''),
                quantity=int(row.get('Quantity', 0)),
                volume=row.get('Volume', ''),
                expiry_date=row.get('Expiry Date', ''),
                safety_notes=row.get('Safety Notes', ''),
                category=row.get('Category', '')
            )
            db.session.add(chem)
            count += 1
        db.session.commit()
        print(f"Imported {count} chemicals!")

with app.app_context():
    import_items('items.csv')
    import_chemicals('chemicals.csv')