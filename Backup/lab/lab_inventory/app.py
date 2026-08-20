from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from datetime import datetime
import csv
import io
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    cupboard = db.Column(db.String(50), nullable=False)
    shelf = db.Column(db.String(50))
    box = db.Column(db.String(50))
    expiry_date = db.Column(db.String(20))
    notes = db.Column(db.String(200))

    def __repr__(self):
        return f"<Item {self.name} ({self.cupboard})>"

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    search = request.args.get('search', '').strip()
    if search:
        items = Item.query.filter(
            or_(
                Item.name.contains(search),
                Item.cupboard.contains(search),
                Item.shelf.contains(search),
                Item.box.contains(search),
                Item.notes.contains(search)
            )
        ).order_by(Item.name.asc()).all()
    else:
        items = Item.query.order_by(Item.name.asc()).all()
    return render_template('index.html', items=items, search=search)

@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        new_item = Item(
            name=request.form['name'].strip(),
            quantity=int(request.form['quantity']),
            cupboard=request.form['cupboard'].strip(),
            shelf=request.form.get('shelf', '').strip(),
            box=request.form.get('box', '').strip(),
            expiry_date=request.form.get('expiry_date', '').strip(),
            notes=request.form.get('notes', '').strip()
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_item.html')

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form['name'].strip()
        item.quantity = int(request.form['quantity'])
        item.cupboard = request.form['cupboard'].strip()
        item.shelf = request.form.get('shelf', '').strip()
        item.box = request.form.get('box', '').strip()
        item.expiry_date = request.form.get('expiry_date', '').strip()
        item.notes = request.form.get('notes', '').strip()
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_item.html', item=item)

@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/cupboard/<cupboard_name>')
def cupboard_view(cupboard_name):
    # fetch all items for this cupboard
    items = Item.query.filter_by(cupboard=cupboard_name).order_by(Item.shelf.asc(), Item.name.asc()).all()
    # group by shelf
    grouped = {}
    for it in items:
        key = it.shelf if (it.shelf and it.shelf.strip()) else "— (no shelf)"
        grouped.setdefault(key, []).append(it)
    # sort shelves with natural-ish order when possible
    def shelf_sort_key(s):
        # try to extract integer if shelf is like '1' or 'Shelf 2' etc.
        import re
        m = re.search(r'(\d+)', s)
        return (0, int(m.group(1))) if m else (1, s.lower())
    sorted_shelves = sorted(grouped.keys(), key=shelf_sort_key)
    return render_template('cupboard_view.html', grouped=grouped, shelves=sorted_shelves, cupboard_name=cupboard_name)

@app.route('/export/csv')
def export_csv():
    # Export all items to CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Quantity", "Cupboard", "Shelf", "Box", "Expiry Date", "Notes"])
    for it in Item.query.order_by(Item.name.asc()).all():
        writer.writerow([it.id, it.name, it.quantity, it.cupboard, it.shelf or "", it.box or "", it.expiry_date or "", it.notes or ""])
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    filename = f"lab_inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype='text/csv')

if __name__ == '__main__':
    # Bind to all interfaces so other PCs on the same LAN can access if needed
    app.run(host='0.0.0.0', port=5000, debug=True)
