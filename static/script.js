// Smooth scrolling for navigation

document.querySelectorAll('nav a[href^="#"]').forEach(link => {
    link.addEventListener("click", function(e) {
        e.preventDefault();

        const target = document.querySelector(this.getAttribute("href"));

        if (target) {
            target.scrollIntoView({
                behavior: "smooth"
            });
        }
    });
});




document.querySelector(".register")
.addEventListener("click",()=>{

    window.location.href="register.html";

});



document.querySelector(".login")
.addEventListener("click",()=>{

    window.location.href="login.html";

});




// Card hover animation


const cards=document.querySelectorAll(".card");


cards.forEach(card=>{


card.addEventListener("mouseenter",()=>{

    card.style.transform="translateY(-10px)";

    card.style.transition=".3s";

});



card.addEventListener("mouseleave",()=>{

    card.style.transform="translateY(0)";

});


});




// Reveal animation on scroll


const sections=document.querySelectorAll(
".card,.steps div,.testimonial,.cta"
);



const observer=new IntersectionObserver(entries=>{


entries.forEach(entry=>{


if(entry.isIntersecting){

entry.target.style.opacity="1";

entry.target.style.transform="translateY(0)";

}


});


});



sections.forEach(section=>{


section.style.opacity="0";

section.style.transform="translateY(40px)";

section.style.transition=".7s";


observer.observe(section);


});