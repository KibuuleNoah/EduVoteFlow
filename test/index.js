let itemCont = document.getElementById("item-cont");
let itemInput = document.getElementById("item-input");

idx = 0;
function addItem() {
  let newItem = document.createElement("div");
  newItem.className = "item";
  newItem.id = `${idx}`;
  newItem.innerHTML = `${itemInput.value} ${idx} <button type="button" onclick="removeItem(${idx})">&times;</button>`;
  itemCont.appendChild(newItem);
  itemInput.value = "";
  ++idx;
}

itemInput.addEventListener("keypress", (event) => {
  if (event.key === "Enter") {
    addItem();
  }
});

function removeItem(id) {
  document.getElementById(`${id}`).remove();
}
