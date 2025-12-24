document.addEventListener('DOMContentLoaded', function() {
    var modal = document.getElementById("about-modal");
    var btn = document.getElementById("about-btn");
    var span = modal.querySelector(".close");

    btn.onclick = function(e) {
        e.preventDefault();
        modal.style.display = "block";
    }

    span.onclick = function() {
        modal.style.display = "none";
    }

    window.addEventListener('click', function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    });
});
