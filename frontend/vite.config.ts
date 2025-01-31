import {defineConfig} from 'vite'
import solid from 'vite-plugin-solid'
import dotenv from 'dotenv'

// if debug variable is not present, then django isn't running in a container (development or build phase)
// and needs to load the env variables from a .env file
if (!process.env.VITE_DEBUG) {
    dotenv.config({path: "../.env"})
}

export default defineConfig({
    plugins: [solid()],
    // if in production/running in docker, add static prefix to all files (where the static files are stored)
    base: process.env.VITE_IN_DOCKER ? "/static/" : "/",
    server: {
        port: 3000,
        proxy: {
            "/api": "http://localhost:" + process.env.VITE_DJANGO_PORT,
        }
    }
})