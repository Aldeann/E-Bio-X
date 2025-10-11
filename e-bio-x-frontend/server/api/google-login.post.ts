import { OAuth2Client } from "google-auth-library";
const config = useRuntimeConfig();
const clientId = config.googleClientId;
const client = new OAuth2Client(clientId);

export default defineEventHandler(async (event) => {
    const body = await readBody(event);
    const token = body.token;

    if (!token) {
        throw createError(
            { statusCode: 400, message: "Token is required" }
        );
    }
    const user = verify(token).catch(console.error);
    
    return user;
});


async function verify(token: string) {
    const ticket = await client.verifyIdToken({
        idToken: token,
        audience: clientId,
    });
    const payload = ticket.getPayload();
    return payload;
}