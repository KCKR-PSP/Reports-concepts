// Minimal runtime for exported canvas boards (.dc.html): {{ expr }} bindings, <sc-for list as>, <sc-if value>,
// event handlers (onClick, onChange, ...) and a DCLogic base class whose setState re-renders the board.
// It is enough to click through a concept. It is not the canvas editor's runtime.
(function () {
  'use strict';

  const exprCache = new Map();
  const failed = new Set();
  function evaluate(expr, scope) {
    let fn = exprCache.get(expr);
    if (!fn) {
      // eslint-disable-next-line no-new-func
      fn = new Function('__scope', 'with (__scope) { return (' + expr + '); }');
      exprCache.set(expr, fn);
    }
    try {
      return fn(scope);
    } catch (error) {
      // Like the canvas: a binding that cannot be read renders empty. Reported once per expression.
      if (!failed.has(expr)) {
        failed.add(expr);
        console.warn('Wyrażenie bez wartości: ' + expr, error.message);
      }
      return undefined;
    }
  }

  const WHOLE = /^\s*\{\{\s*([\s\S]+?)\s*\}\}\s*$/;
  const PART = /\{\{\s*([\s\S]+?)\s*\}\}/g;
  const whole = (value) => {
    const match = WHOLE.exec(value || '');
    return match ? match[1] : null;
  };
  const text = (value, scope) =>
    value.replace(PART, (_, expr) => {
      const result = evaluate(expr, scope);
      return result === undefined || result === null || result === false ? '' : String(result);
    });

  function build(node, scope, parent) {
    if (node.nodeType === Node.TEXT_NODE) {
      parent.appendChild(document.createTextNode(text(node.nodeValue, scope)));
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const tag = node.localName;
    // <sc-for>/<sc-if>, or <template data-sc="for|if"> (the build's form, safe inside tables).
    const kind = tag === 'sc-for' || tag === 'sc-if' ? tag.slice(3) : tag === 'template' ? node.getAttribute('data-sc') : null;
    // A <template> inside <svg> is an SVG element without .content: its children are ordinary child nodes.
    const kids = tag === 'template' && node.content ? node.content.childNodes : node.childNodes;
    if (kind === 'for') {
      const list = evaluate(whole(node.getAttribute('list')), scope) || [];
      const as = node.getAttribute('as');
      list.forEach((item, index) => {
        const inner = Object.create(scope);
        inner[as] = item;
        inner.index = index;
        inner.$index = index;
        kids.forEach((child) => build(child, inner, parent));
      });
      return;
    }
    if (kind === 'if') {
      if (evaluate(whole(node.getAttribute('value')), scope)) kids.forEach((child) => build(child, scope, parent));
      return;
    }
    const element = document.createElementNS(node.namespaceURI, tag);
    let value;
    for (const attribute of node.attributes) {
      const expr = whole(attribute.value);
      if (/^on/i.test(attribute.name) && expr) {
        const handler = evaluate(expr, scope);
        let event = attribute.name.slice(2).toLowerCase();
        // React-style onChange: text fields report every keystroke, so buttons enabled by them work on the first click.
        const typing = tag === 'textarea' || (tag === 'input' && !/^(checkbox|radio|date|range|file)$/.test(node.getAttribute('type') || ''));
        if (event === 'change' && typing) event = 'input';
        if (typeof handler === 'function') element.addEventListener(event, handler);
        continue;
      }
      if ((attribute.name === 'checked' || attribute.name === 'disabled' || attribute.name === 'selected') && expr) {
        element[attribute.name] = !!evaluate(expr, scope);
        continue;
      }
      if (attribute.name === 'value' && expr && /^(input|textarea|select)$/.test(tag)) {
        value = evaluate(expr, scope);
        continue;
      }
      element.setAttribute(attribute.name, text(attribute.value, scope));
    }
    node.childNodes.forEach((child) => build(child, scope, element));
    if (value !== undefined) element.value = value === null ? '' : value;
    parent.appendChild(element);
  }

  let renderBoard = () => {};
  class DCLogic {
    constructor() {
      this.props = {};
    }
    setState(patch) {
      Object.assign(this.state, typeof patch === 'function' ? patch(this.state) : patch);
      renderBoard();
    }
    forceUpdate() {
      renderBoard();
    }
  }
  window.DCLogic = DCLogic;

  // Mounts the board: template (a <template> element), the board's Component class and its props.
  window.mountBoard = function mountBoard(root, template, Component, props) {
    const component = new Component();
    component.props = Object.assign({}, props);
    renderBoard = () => {
      const scroll = [window.scrollX, window.scrollY];
      // Re-rendering replaces the DOM: keep focus and caret on the same field (by its position among the fields).
      const fields = () => Array.from(root.querySelectorAll('input, textarea, select, button, a[href]'));
      const active = document.activeElement;
      const focusAt = root.contains(active) ? fields().indexOf(active) : -1;
      const caret = active && typeof active.selectionStart === 'number' ? [active.selectionStart, active.selectionEnd] : null;
      const scope = component.renderVals();
      const fragment = document.createDocumentFragment();
      template.content.childNodes.forEach((child) => build(child, scope, fragment));
      root.replaceChildren(fragment);
      if (focusAt >= 0) {
        const again = fields()[focusAt];
        if (again) {
          again.focus({ preventScroll: true });
          if (caret && typeof again.setSelectionRange === 'function') {
            try { again.setSelectionRange(caret[0], caret[1]); } catch (error) { /* type without a caret */ }
          }
        }
      }
      window.scrollTo(scroll[0], scroll[1]);
    };
    renderBoard();
    // Like React: lifecycle hook after the first render (timers, e.g. the IGO stopwatch).
    if (typeof component.componentDidMount === 'function') component.componentDidMount();
    return {
      setProps(patch) {
        Object.assign(component.props, patch);
        renderBoard();
      },
    };
  };
})();
