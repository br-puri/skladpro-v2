(() => {
  const $ = id => document.getElementById(id);
  const input = $('product-photo-input'), preview = $('photo-preview'), dialog = $('photo-crop-dialog');
  const canvas = $('crop-canvas'), ctx = canvas.getContext('2d');
  const ratio = $('crop-ratio'), zoom = $('crop-zoom'), x = $('crop-x'), y = $('crop-y');
  let original = preview.getAttribute('src'), sourceURL, previewURL, image, drag, busy = false, version = 0;
  function reset() { ratio.value = '1'; zoom.value = '1'; x.value = y.value = '0.5'; $('crop-free').value = '1'; draw(); }
  function rect() {
    const r = ratio.value === 'original' ? image.width / image.height : Number(ratio.value === 'free' ? $('crop-free').value : ratio.value);
    let w = Math.min(image.width, image.height * r) / Number(zoom.value), h = w / r;
    return {w, h, sx: (image.width-w)*Number(x.value), sy: (image.height-h)*Number(y.value)};
  }
  function draw() {
    $('crop-free-label').hidden = ratio.value !== 'free';
    document.querySelectorAll('[data-crop-ratio]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.cropRatio === ratio.value)));
    $('crop-zoom-value').textContent = Math.round(Number(zoom.value)*100) + '%';
    if (!image) return;
    const r = rect(), scale = Math.min(1000/r.w,600/r.h);
    canvas.width = Math.max(1,Math.round(r.w*scale)); canvas.height = Math.max(1,Math.round(r.h*scale));

    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.drawImage(image,r.sx,r.sy,r.w,r.h,0,0,canvas.width,canvas.height);
  }
  input.addEventListener('change', () => {
    version++;
    if (sourceURL) URL.revokeObjectURL(sourceURL);
    sourceURL = input.files[0] ? URL.createObjectURL(input.files[0]) : null;
    original = sourceURL;
    if (original) { preview.src = original; $('photo-preview-wrap').hidden = false; $('open-photo-crop').hidden = false; }
    $('photo-crop-status').textContent = 'Photo selected. Use Crop photo to adjust it before saving.';
  });
  $('open-photo-crop').addEventListener('click', async () => {
    if (!original) return;
    $('crop-error').textContent = ''; $('crop-apply').disabled = true; image = null;
    ctx.clearRect(0,0,canvas.width,canvas.height); dialog.showModal();
    const current = ++version;
    const loaded = new Image(); loaded.crossOrigin = 'anonymous';
    loaded.onload = () => { if (current !== version || !dialog.open) return; image = loaded; reset(); $('crop-apply').disabled = false; };
    loaded.onerror = () => { if (current === version) $('crop-error').textContent = 'Could not open this photo for cropping. Choose the original image file and try again.'; };
    loaded.src = original;
  });
  document.querySelectorAll('[data-crop-ratio]').forEach(button => button.addEventListener('click', () => { ratio.value = button.dataset.cropRatio; draw(); }));
  $('crop-close').addEventListener('click',()=>dialog.close());
  [ratio,zoom,x,y,$('crop-free')].forEach(el => el.addEventListener('input',draw));
  canvas.addEventListener('pointerdown', e => { if (!image) return; drag={x:e.clientX,y:e.clientY,px:Number(x.value),py:Number(y.value)}; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => {
    if (!drag || !image) return;
    const r=rect(), bounds=canvas.getBoundingClientRect();
    x.value = Math.max(0,Math.min(1,drag.px-(e.clientX-drag.x)/bounds.width*r.w/Math.max(1,image.width-r.w)));
    y.value = Math.max(0,Math.min(1,drag.py-(e.clientY-drag.y)/bounds.height*r.h/Math.max(1,image.height-r.h))); draw();
  });
  ['pointerup','pointercancel','lostpointercapture'].forEach(event=>canvas.addEventListener(event,()=>drag=null));
  $('crop-reset').addEventListener('click',reset);
  $('crop-cancel').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('close',()=>{version++;drag=null;});
  $('crop-apply').addEventListener('click', () => {
    if (!image || busy) return;
    busy=true; $('crop-apply').disabled=true;
    const current=version, r=rect(), output=document.createElement('canvas'), scale=Math.min(1,1200/r.w,1200/r.h);
    output.width=Math.max(1,Math.round(r.w*scale)); output.height=Math.max(1,Math.round(r.h*scale));
    try {
      output.getContext('2d').drawImage(image,r.sx,r.sy,r.w,r.h,0,0,output.width,output.height);
      output.toBlob(blob=>{
        try {
          if (current !== version || !dialog.open) return;
          if (!blob) throw new Error('Could not create the crop.');
          const transfer=new DataTransfer(); transfer.items.add(new File([blob],'product-crop.png',{type:'image/png'})); input.files=transfer.files;
          if (previewURL) URL.revokeObjectURL(previewURL);
          previewURL=URL.createObjectURL(blob); preview.src=previewURL;
          $('photo-crop-status').textContent='Crop ready. Save the product to apply it. Transparent backgrounds are preserved.';
          dialog.close();
        } catch (err) { $('crop-error').textContent=err.message; }
        finally { busy=false; $('crop-apply').disabled=false; }
      },'image/png');
    } catch (err) { busy=false; $('crop-apply').disabled=false; $('crop-error').textContent='This image cannot be cropped here. Choose the original file and try again.'; }
  });
})();
