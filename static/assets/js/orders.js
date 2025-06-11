document.addEventListener('DOMContentLoaded', function () {
    // Client-side sorting for order listing table
    const table = document.querySelector('.order__table tbody');
    if (table) {
        new Sortable(table, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            onEnd: function () {
                // No server-side update needed
            },
        });

        document.querySelectorAll('.order__table th').forEach(header => {
            header.addEventListener('click', function () {
                const sortType = this.getAttribute('data-sort');
                const rows = Array.from(table.querySelectorAll('tr'));
                const index = Array.from(this.parentNode.children).indexOf(this);

                rows.sort((a, b) => {
                    let aValue = a.children[index].getAttribute('data-sort-value') || a.children[index].textContent;
                    let bValue = b.children[index].getAttribute('data-sort-value') || b.children[index].textContent;

                    if (sortType === 'float') {
                        aValue = parseFloat(aValue);
                        bValue = parseFloat(bValue);
                        return aValue - bValue;
                    } else if (sortType === 'date') {
                        aValue = new Date(aValue);
                        bValue = new Date(bValue);
                        return aValue - bValue;
                    } else {
                        return aValue.localeCompare(bValue);
                    }
                });

                if (this.classList.contains('sorted-asc')) {
                    rows.reverse();
                    this.classList.remove('sorted-asc');
                    this.classList.add('sorted-desc');
                } else {
                    this.classList.remove('sorted-desc');
                    this.classList.add('sorted-asc');
                }

                table.innerHTML = '';
                rows.forEach(row => table.appendChild(row));
            });
        });
    }

    // Modal handling for cancellation
    const cancelModal = document.getElementById('cancelModal');
    if (cancelModal) {
        document.querySelectorAll('.cancel-btn').forEach(button => {
            button.addEventListener('click', function () {
                document.getElementById('cancel-item-id').value = this.dataset.itemId;
                document.getElementById('cancel-reason').value = '';
                document.getElementById('cancel-other').value = '';
                document.getElementById('cancel-other-reason').style.display = 'none';
            });
        });

        document.getElementById('cancel-reason').addEventListener('change', function () {
            document.getElementById('cancel-other-reason').style.display = this.value === 'Other' ? 'block' : 'none';
        });

        document.getElementById('cancel-form').addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);
            const itemId = formData.get('item_id');
            const statusCell = document.querySelector(`tr td.status-${itemId}`);
            const orderStatusCell = document.querySelector('.order__details .status');

            fetch(`/orders/cancel/${itemId}/`, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    // Update status dynamically
                    if (statusCell) {
                        statusCell.textContent = data.new_status;
                        statusCell.className = `status-${data.new_status.toLowerCase().replace(' ', '_')} status-${itemId}`;
                    }
                    if (orderStatusCell) {
                        orderStatusCell.textContent = data.order_status;
                        orderStatusCell.className = `status status-${data.order_status.toLowerCase().replace(' ', '_')}`;
                    }
                    // Hide modal and disable button
                    bootstrap.Modal.getInstance(cancelModal).hide();
                    document.querySelector(`.cancel-btn[data-item-id="${itemId}"]`).disabled = true;
                } else {
                    alert(data.message);
                }
            })
            .catch(error => alert('An error occurred. Please try again.'));
        });
    }

    // Modal handling for return
    const returnModal = document.getElementById('returnModal');
    if (returnModal) {
        document.querySelectorAll('.return-btn').forEach(button => {
            button.addEventListener('click', function () {
                document.getElementById('return-item-id').value = this.dataset.itemId;
                document.getElementById('return-reason').value = '';
                document.getElementById('return-other').value = '';
                document.getElementById('return-other-reason').style.display = 'none';
            });
        });

        document.getElementById('return-reason').addEventListener('change', function () {
            document.getElementById('return-other-reason').style.display = this.value === 'Other' ? 'block' : 'none';
        });

        document.getElementById('return-form').addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);
            const itemId = formData.get('item_id');
            const statusCell = document.querySelector(`tr td.status-${itemId}`);
            const orderStatusCell = document.querySelector('.order__details .status');

            fetch(`/orders/return/${itemId}/`, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    // Update status dynamically
                    if (statusCell) {
                        statusCell.textContent = data.new_status;
                        statusCell.className = `status-${data.new_status.toLowerCase().replace(' ', '_')} status-${itemId}`;
                    }
                    if (orderStatusCell) {
                        orderStatusCell.textContent = data.order_status;
                        orderStatusCell.className = `status status-${data.order_status.toLowerCase().replace(' ', '_')}`;
                    }
                    // Hide modal and disable button
                    bootstrap.Modal.getInstance(returnModal).hide();
                    document.querySelector(`.return-btn[data-item-id="${itemId}"]`).disabled = true;
                } else {
                    alert(data.message);
                }
            })
            .catch(error => alert('An error occurred. Please try again.'));
        });
    }
});