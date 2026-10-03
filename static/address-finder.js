(() => {
  document.querySelectorAll('input[name="postcode"], input[name="co_postcode"], input[name="co_delivery_postcode"]').forEach(input => {
    const form = input.form;
    if (!form) return;
    const prefix = input.name.slice(0, -'postcode'.length);
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'btn btn-secondary';
    button.textContent = 'Find UK address'; button.style.marginTop = '8px';
    const status = document.createElement('div');
    status.setAttribute('role', 'status');
    status.style.cssText = 'font-size:12px;margin-top:6px;color:#475569';
    const select = document.createElement('select');
    select.className = 'form-control'; select.hidden = true;
    select.style.marginTop = '8px'; select.setAttribute('aria-label', 'Choose full address');
    input.after(button, status, select);
    let addresses = [], generation = 0;
    input.addEventListener('input', () => { generation++; select.hidden = true; status.textContent = ''; });
    button.addEventListener('click', async () => {
      const current = ++generation;
      button.disabled = true; select.hidden = true; status.textContent = 'Finding addresses…';
      try {
        const response = await fetch('/api/address-lookup?postcode=' + encodeURIComponent(input.value.trim()), {headers:{Accept:'application/json'}});
        const result = await response.json();
        if (current !== generation) return;
        if (!response.ok) throw new Error(result.error || 'Address lookup failed. You can enter the address manually.');
        addresses = result.addresses || [];
        select.replaceChildren(new Option('Choose your address…', ''));
        addresses.forEach((address,index) => select.add(new Option(address.label, String(index))));
        select.hidden = !addresses.length;
        status.textContent = addresses.length ? 'Choose an address below to fill the form.' : 'No addresses found. Check the postcode or enter the address manually.';
        if (addresses.length) select.focus();
      } catch (error) {
        if (current === generation) status.textContent = error instanceof SyntaxError ? 'Please sign in again or try later. You can enter the address manually.' : error.message;
      } finally { button.disabled = false; }
    });
    select.addEventListener('change', () => {
      if (select.value === '') return;
      const address = addresses[Number(select.value)];
      for (const key of ['address','address2','city','postcode','country']) {
        const field = form.elements.namedItem(prefix + key);
        if (!field) continue;
        if (field.tagName === 'SELECT' && !Array.from(field.options).some(o => o.value === address[key])) field.add(new Option(address[key], address[key]));
        field.value = address[key]; field.dispatchEvent(new Event('change', {bubbles:true}));
      }
      status.textContent = 'Address filled in. You can edit it before saving.';
    });
  });
})();
