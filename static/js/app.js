document.addEventListener("DOMContentLoaded", () => {

    const btn = document.getElementById("themeToggle");

    if(btn){

        btn.addEventListener("click", ()=>{

            const isDark =
                document.documentElement.classList.toggle("dark");

            fetch("/api/user/settings",{

                method:"POST",

                headers:{
                    "Content-Type":"application/json"
                },

                body:JSON.stringify({

                    theme_preference:isDark?"dark":"light"

                })

            });

        });

    }

});