import {createSignal, onMount} from "solid-js";
import Navbar from "../components/Navbar.tsx";
import Footer from "../components/Footer.tsx";
import {FiKey} from "solid-icons/fi";
import {clsx} from "clsx";
import axios from "axios";

const AccessKeys = () => {
    const [accessKey, setAccessKey] = createSignal("")
    const [validKey, setValidKey] = createSignal(true)
    const [apiResponse, setApiResponse] = createSignal("")
    const [buttonEnabled, setButtonEnabled] = createSignal(true)

    onMount(() => document.title = "Access Keys");

    const handleSubmit = async (event: any) => {
        event.preventDefault();
        if (!buttonEnabled()) {
            return
        }
        setButtonEnabled(false)

        try {
            const response = await axios({
                method: "POST",
                url: "/api/activateaccesskey/",
                headers: {
                    "Content-Type": "application/json",
                },
                data: {
                    access_key: accessKey(),
                }
            })

            setApiResponse(response.data)
            setValidKey(true)
            setAccessKey("")
        } catch (error: any) {
            setApiResponse(error.response.data)
            setValidKey(false)
        }

        setButtonEnabled(true)
    }

    return (
        <div class="flex flex-col min-h-screen w-full bg-bg_gray">
            <Navbar/>
            <div class="flex flex-col flex-grow self-center items-center font-code mt-[10%] p-4 w-full sm:w-1/3">
                <h1 class="text-3xl text-center">Access Keys</h1>
                <form class="mt-8 w-full flex flex-col items-center" onSubmit={handleSubmit}>
                    <div
                        class={clsx("flex border-b-2 border-gray-300 w-full items-center justify-center transition duration-300", {
                            "hover:border-gray-400 focus-within:border-gray-400": validKey(),
                            "border-amber-700": !validKey(),
                        })}>
                        <label for="access_key"><FiKey class="size-6" stroke-width={1.3}/></label>
                        <input value={accessKey()} onInput={(e) => setAccessKey(e.target.value)}
                               class={"w-full ml-1 text-lg bg-transparent outline-none"}
                               placeholder={"Access Key here"} type="text" id="access_key"/>
                    </div>
                    <h1 class="text-md mt-2">{apiResponse()}</h1>
                    <button type="submit" class={clsx("font-ibm text-xl w-fit p-2 transition duration-300", {
                        "text-black/50 pointer-events-none": !buttonEnabled(),
                        "hover:shadow-lg": buttonEnabled(),
                    })}>
                        Activate
                    </button>
                </form>
                <h1 class="text-xl font-semibold mt-10">
                    What are Access Key?
                </h1>
                <h1 class="text-lg mt-1">
                    An Access Key is a key that can be activated to change which roles you account has.
                    <br/>
                    For example, you could use an Access Key to gain access to the <a class="text-primary"
                                                                                      href={"/keyclub"}>Key
                    Club</a> logging bot.
                    <br/>
                    Access Keys are single use, and can only be created and given out by an administrator.
                    You must be logged into your account in order to use an Access Key.
                </h1>
            </div>
            <Footer/>
        </div>
    )
}

export default AccessKeys;