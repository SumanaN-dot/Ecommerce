const products=[
 {id:1,name:'Stoneware Mug',category:'Tableware',price:28,type:'mug',bg:'#dcd4c5'},
 {id:2,name:'Moss Table Lamp',category:'Lighting',price:119,type:'lamp',bg:'#d2d2c3'},
 {id:3,name:'Olive Carafe',category:'Kitchen',price:44,type:'bottle',bg:'#c3c9bd'},
 {id:4,name:'Canvas Market Tote',category:'Everyday carry',price:36,type:'tote',bg:'#dfd0bc'}
];
const cart=[];
const grid=document.querySelector('#productGrid');
function money(v){return new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(v)}
function renderProducts(){grid.innerHTML=products.map(p=>`<article class="product-card"><div class="product-image" style="background:${p.bg}"><div class="shape ${p.type}"></div></div><div class="product-meta"><h3>${p.name}</h3><p>${p.category} · ${money(p.price)}</p><button aria-label="Add ${p.name}" onclick="addToCart(${p.id})">+</button></div></article>`).join('')}
window.addToCart=(id)=>{const p=products.find(x=>x.id===id);const item=cart.find(x=>x.id===id);item?item.qty++:cart.push({...p,qty:1});renderCart();showToast(`${p.name} added to bag`)};
function renderCart(){document.querySelector('#cartCount').textContent=cart.reduce((s,i)=>s+i.qty,0);const box=document.querySelector('#cartItems');box.innerHTML=cart.length?cart.map(i=>`<div class="cart-item"><div class="cart-swatch">${i.qty}×</div><div><h4>${i.name}</h4><p>${i.category}</p></div><strong>${money(i.price*i.qty)}</strong></div>`).join(''):'<p class="empty">Your bag is empty.</p>';document.querySelector('#subtotal').textContent=money(cart.reduce((s,i)=>s+i.price*i.qty,0))}
function toggleCart(open){document.querySelector('#cartDrawer').classList.toggle('open',open);document.querySelector('#overlay').classList.toggle('open',open);document.querySelector('#cartDrawer').setAttribute('aria-hidden',String(!open))}
document.querySelector('#cartButton').onclick=()=>toggleCart(true);document.querySelector('#closeCart').onclick=()=>toggleCart(false);document.querySelector('#overlay').onclick=()=>toggleCart(false);
document.querySelector('#newsletterForm').onsubmit=e=>{e.preventDefault();showToast('You’re on the list. Welcome!');e.target.reset()};
function showToast(msg){const t=document.querySelector('#toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2200)}
renderProducts();
