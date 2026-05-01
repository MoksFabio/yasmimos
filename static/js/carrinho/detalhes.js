document.addEventListener('DOMContentLoaded', function () {

    function updateSummary(data) {
        if (data.cart_total !== undefined) {
            document.getElementById('subtotal-amount').innerText = data.cart_total;
        }
        
        if (data.discount !== undefined) {
            const dr = document.getElementById('discount-row');
            const da = document.getElementById('discount-amount');
            if (parseFloat(data.discount.toString().replace(',','.')) > 0) {
                dr.style.display = 'flex';
                da.innerText = data.discount;
                if(data.coupon_code) {
                    dr.querySelector('span').innerText = 'Cupom de desconto (' + data.coupon_code + ')';
                }
            } else {
                dr.style.display = 'none';
            }
        }
        
        if (data.tip !== undefined) {
            const tr = document.getElementById('tip-row');
            const ta = document.getElementById('tip-amount');
            const tipVal = parseFloat(data.tip.toString().replace(',','.'));
            if (tipVal > 0) {
                tr.style.display = 'flex';
                ta.innerText = data.tip;
            } else {
                tr.style.display = 'none';
            }
        }
        
        if (data.cart_total_after_discount !== undefined) {
            document.getElementById('payment-total-amount').innerText = data.cart_total_after_discount;
            document.getElementById('bottom-total-amount').innerText = data.cart_total_after_discount;
        } else if (data.cart_total !== undefined && data.discount === undefined && data.tip === undefined) {
            document.getElementById('payment-total-amount').innerText = data.cart_total;
            document.getElementById('bottom-total-amount').innerText = data.cart_total;
        }
    }

    function showMessage(msg, isSuccess) {
        const msgArea = document.getElementById('message-area');
        msgArea.innerHTML = '';
        const msgDiv = document.createElement('div');
        msgDiv.innerText = msg;
        msgDiv.style.color = isSuccess ? 'var(--success-color)' : 'var(--error-color)';
        msgDiv.style.marginTop = '5px';
        msgArea.appendChild(msgDiv);
        setTimeout(() => {
            msgDiv.style.transition = 'opacity 0.5s ease';
            msgDiv.style.opacity = '0';
            setTimeout(() => msgDiv.remove(), 500);
        }, 3000);
    }

    // Coupon Apply
    const couponForm = document.getElementById('coupon-form');
    if (couponForm) {
        couponForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const btn = couponForm.querySelector('button[type="submit"]');
            const originalText = btn.innerText;
            btn.innerText = '...';
            btn.disabled = true;

            fetch(couponForm.action, {
                method: 'POST',
                body: new FormData(couponForm),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    updateSummary({
                        subtotal: data.subtotal,
                        discount: data.discount,
                        coupon_code: data.coupon_code,
                        cart_total_after_discount: parseFloat(data.total).toFixed(2).replace('.', ',')
                    });
                    showMessage(data.message, true);
                } else {
                    showMessage(data.message, false);
                }
            })
            .catch(err => showMessage('Erro ao processar cupom.', false))
            .finally(() => { btn.innerText = originalText; btn.disabled = false; });
        });
    }

    // Gorjeta Apply
    const tipForm = document.getElementById('tip-form');
    if (tipForm) {
        tipForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const btn = tipForm.querySelector('button[type="submit"]');
            const originalText = btn.innerText;
            btn.innerText = '...';
            btn.disabled = true;

            fetch(tipForm.action, {
                method: 'POST',
                body: new FormData(tipForm),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => {
                const rmBtn = document.getElementById('remove-tip-btn');
                const chevBtn = document.querySelector('.icon-chevron-tip');
                if (data.success) {
                    updateSummary({
                        tip: data.tip,
                        cart_total_after_discount: parseFloat(data.cart_total_after_discount.replace(',','.')).toFixed(2).replace('.', ',')
                    });
                    const tipValue = parseFloat(data.tip.replace(',', '.'));
                    if (tipValue > 0) {
                        if(rmBtn) rmBtn.style.display = 'inline-block';
                        if(chevBtn) chevBtn.style.display = 'none';
                        showMessage('Gorjeta adicionada!', true);
                    } else {
                        if(rmBtn) rmBtn.style.display = 'none';
                        if(chevBtn) chevBtn.style.display = 'inline-block';
                        showMessage('Gorjeta removida.', true);
                    }
                } else {
                    showMessage(data.error || 'Erro', false);
                }
            })
            .catch(err => showMessage('Erro processando gorjeta.', false))
            .finally(() => { btn.innerText = originalText; btn.disabled = false; });
        });

        const removeTipBtn = document.getElementById('remove-tip-btn');
        if (removeTipBtn) {
            removeTipBtn.addEventListener('click', function() {
                document.getElementById('tip_amount').value = '';
                tipForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            });
        }
    }

    // Ajax Quantity Updates
    document.querySelectorAll('.ajax-cart-form').forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const box = this.closest('.cart-item');
            box.style.opacity = '0.5';
            
            fetch(this.getAttribute('action'), {
                method: 'POST',
                body: new FormData(this),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    if (data.item_quantity === 0) {
                        box.remove();
                        if(data.cart_quantity === 0) window.location.reload();
                    } else {
                        const qtyDisplay = box.querySelector('.quantity-display');
                        if (qtyDisplay) qtyDisplay.innerText = data.item_quantity;
                        const itemTotal = box.querySelector('.item-total-price');
                        if (itemTotal) itemTotal.innerText = 'R$ ' + data.item_total;
                    }
                    updateSummary({
                        cart_total: data.cart_total,
                        discount: data.discount,
                        cart_total_after_discount: data.cart_total_after_discount !== undefined ? data.cart_total_after_discount : data.cart_total
                    });
                    
                    const checkoutBtn = document.querySelector('.btn-checkout');
                    if(checkoutBtn && data.cart_quantity > 0) checkoutBtn.innerText = 'Confirmar (' + data.cart_quantity + ')';
                }
            })
            .finally(() => { box.style.opacity = '1'; });
        });
    });

    // Ajax Remove completely
    document.querySelectorAll('.ajax-cart-remove').forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const box = this.closest('.cart-item');
            box.style.opacity = '0.3';
            
            fetch(this.getAttribute('action'), {
                method: 'POST',
                body: new FormData(this),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    box.remove();
                    if(data.cart_quantity === 0) window.location.reload();
                    
                    updateSummary({
                        cart_total: data.cart_total,
                        cart_total_after_discount: data.cart_total_after_discount !== undefined ? data.cart_total_after_discount : data.cart_total
                    });
                    
                    const checkoutBtn = document.querySelector('.btn-checkout');
                    if(checkoutBtn && data.cart_quantity > 0) checkoutBtn.innerText = 'Confirmar (' + data.cart_quantity + ')';
                } else {
                    box.style.opacity = '1';
                }
            });
        });
    });

    // Ajax Suggested Add
    document.querySelectorAll('.ajax-add-suggestion').forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const btn = this.querySelector('button');
            const originalText = btn.innerText;
            btn.innerText = '...';
            
            fetch(this.getAttribute('action'), {
                method: 'POST',
                body: new FormData(this),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    btn.innerHTML = '<i class="fas fa-check"></i>';
                    btn.style.background = 'var(--success-color)';
                    setTimeout(() => window.location.reload(), 300);
                } else {
                    btn.innerText = originalText;
                }
            });
        });
    });

});

    // Helper functions for Payment UI
    window.togglePaymentInfo = function(method) {
        document.getElementById('info-pix').style.display = method === 'pix' ? 'block' : 'none';
        const infoPoint = document.getElementById('info-point');
        if (infoPoint) infoPoint.style.display = method === 'point' ? 'block' : 'none';
        document.getElementById('info-cash').style.display = method === 'cash' ? 'block' : 'none';
    };

    window.toggleClientInfo = function(show) {
        const infoDiv = document.getElementById('superuser-client-info');
        if (infoDiv) {
            infoDiv.style.display = show ? 'block' : 'none';
        }
    };

    window.handleClientSelect = function(selectElement) {
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        const clientNameInput = document.getElementById('client_name');
        const clientPhoneInput = document.getElementById('client_phone');

        if (selectedOption.value) {
            let name = selectedOption.getAttribute('data-name').trim();
            if (!name) name = selectedOption.getAttribute('data-username').trim();

            clientNameInput.value = name;
            clientPhoneInput.value = selectedOption.getAttribute('data-phone').trim();
        } else {
            clientNameInput.value = '';
            clientPhoneInput.value = '';
        }
    };