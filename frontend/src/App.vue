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
    background-color: #f8f9fa;
    color: #333;
    line-height: 1.6;
}

.app-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}
</style>
