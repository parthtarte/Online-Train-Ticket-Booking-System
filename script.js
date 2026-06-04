document.addEventListener('DOMContentLoaded', () => {
    console.log('RailEase UI v2.0 initialized');

    // Smooth button clicks
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            // Check if it's a submit button
            if (this.type === 'submit' && this.closest('form').checkValidity()) {
                const text = this.innerText;
                const spinner = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>';
                this.innerHTML = spinner + text;
                this.style.pointerEvents = 'none';
                this.style.opacity = '0.8';
            }
        });
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s ease';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // Seat selection tracking logs
    const seats = document.querySelectorAll('input[name="seat_no"]');
    seats.forEach(seat => {
        seat.addEventListener('change', () => {
            if (seat.checked) {
                console.log(`Seat selected: ${seat.value}`);
            }
        });
    });
});
