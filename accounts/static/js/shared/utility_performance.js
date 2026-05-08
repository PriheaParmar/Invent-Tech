(function(){
  function enhanceSelect(select){
    if(!select || select.dataset.utilityEnhanced === '1') return;
    if(select.options.length < 18) return;
    select.dataset.utilityEnhanced = '1';
    var box = document.createElement('div');
    box.className = 'ut-select-filter';
    var input = document.createElement('input');
    input.type = 'search';
    input.placeholder = 'Search options...';
    input.setAttribute('aria-label','Search dropdown options');
    box.appendChild(input);
    select.parentNode.insertBefore(box, select);
    var original = Array.prototype.map.call(select.options, function(opt){
      return {value: opt.value, text: opt.text, selected: opt.selected, disabled: opt.disabled};
    });
    input.addEventListener('input', function(){
      var term = input.value.trim().toLowerCase();
      var currentValue = select.value;
      select.innerHTML = '';
      original.forEach(function(opt){
        if(!term || opt.text.toLowerCase().indexOf(term) !== -1 || opt.selected || opt.value === ''){
          var node = document.createElement('option');
          node.value = opt.value;
          node.text = opt.text;
          node.disabled = opt.disabled;
          node.selected = opt.value === currentValue;
          select.appendChild(node);
        }
      });
    });
  }
  function init(root){
    root = root || document;
    root.querySelectorAll('select').forEach(enhanceSelect);
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', function(){ init(document); });
  }else{ init(document); }
  document.addEventListener('erp:modal-loaded', function(e){ init(e.target || document); });
})();
