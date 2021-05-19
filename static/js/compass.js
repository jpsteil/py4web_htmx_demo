var dropdown = document.querySelector('.dropdown');
if (dropdown != null) {
  dropdown.addEventListener('click', function(event) {
    event.stopPropagation();
    dropdown.classList.toggle('is-active');
  });
}