<template>
    <div class="app-container">
        <router-view />
    </div>
</template>

<script>
export default {
    name: "App",
};
</script>

<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: "Inter", sans-serif;
    background-color: #f0f4f8;
    color: #333;
    line-height: 1.6;
    min-height: 100vh;
    background-image: linear-gradient(120deg, #fdfbfb 0%, #ebedee 100%);
}

.app-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}
</style>
