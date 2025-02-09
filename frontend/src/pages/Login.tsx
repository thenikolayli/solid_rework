import {createSignal, onMount, useContext} from "solid-js";
import {useNavigate} from "@solidjs/router";
import {FiLock, FiUser} from "solid-icons/fi";
import {clsx} from "clsx";
import axios from "axios";
import UserDataContext from "../util/Context.tsx";
import Navbar from "../components/Navbar.tsx";
import Footer from "../components/Footer.tsx";
import InputField from "../components/InputField.tsx";

const Login = () => {
    const [inputData, setInputData] = createSignal<{[key: string]: {[key: string]: any}}>({
        "username": {"value": "", "valid": true, "message": ""},
        "password": {"value": "", "valid": true, "message": ""}
    })
    const [buttonEnabled, setButtonEnabled] = createSignal(true)
    const context: any = useContext(UserDataContext)
    const navigate = useNavigate();

    onMount(async () => {
        await context.refreshToken()
        if (context.userData() !== "") {
            navigate("/")
        }
        document.title = "Login"
    })

    const handleSubmit = async (event: any) => {
        event.preventDefault()
        if (!buttonEnabled()) {
            return
        }
        setButtonEnabled(false)
        let newInputData = {...inputData()}

        if (inputData()["username"]["value"] == "") {
            newInputData["username"]["message"] = "username required"
            newInputData["username"]["valid"] = false
            setInputData(newInputData)
            return
        }
        if (inputData()["password"]["value"] == "") {
            newInputData["password"]["message"] = "password required"
            newInputData["password"]["valid"] = false
            setInputData(newInputData)
            return
        }

        try {
            const response = await axios({
                method: 'POST',
                url: "/api/login/",
                headers: {
                   "Content-Type": "application/json",
                },
                data: {
                   username: inputData()["username"]["value"],
                   password: inputData()["password"]["value"],
                }
            })

            if (response.status === 200) {
                context.setUserData(JSON.stringify(response.data))
                navigate("/")
            }
        } catch (error: any) {
           newInputData["password"]["message"] = "invalid credentials"
           newInputData["username"]["valid"] = false
           newInputData["password"]["valid"] = false
        }

        setInputData(newInputData)
        setButtonEnabled(true)
    }

    return (
        <div class="flex flex-col min-h-screen w-full bg-bg_gray">
            <Navbar />
            <div class="flex flex-col flex-grow self-center items-center font-code mt-[10%] p-4 w-full sm:w-1/3">
                <h1 class="text-3xl">Login</h1>
                <form onSubmit={handleSubmit} class="container w-fit mt-4 mb-8 space-y-1">
                    <InputField inputData={inputData} setInputData={setInputData} Icon={FiUser} input="username" inputType="text" />
                    <InputField inputData={inputData} setInputData={setInputData} Icon={FiLock} input="password" inputType="password" />
                    <button type="submit"
                            class={clsx("flex justify-self-center text-2xl font-ibm p-1 transition duration-300", {
                                "text-black/50 pointer-events-none": !buttonEnabled(),
                                "hover:shadow-lg": buttonEnabled(),
                            })}>Enter
                    </button>
                </form>
            </div>
            <Footer/>
        </div>
    )
}

export default Login