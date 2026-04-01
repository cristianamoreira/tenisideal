exports.handler = async function (event, context) {
    const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, x-api-key, anthropic-version',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    };

    if (event.httpMethod === 'OPTIONS') {
        return { statusCode: 200, headers, body: '' };
    }

    if (event.httpMethod !== 'POST') {
        return { statusCode: 405, headers, body: 'Method Not Allowed' };
    }

    try {
        let rawBody;
        try {
            rawBody = JSON.parse(event.body);
        } catch (e) {
            return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid JSON body' }) };
        }

        const apiKey = event.headers['x-api-key'] || event.headers['X-Api-Key'];
        const anthropicVersion = event.headers['anthropic-version'] || event.headers['Anthropic-Version'] || '2023-06-01';

        if (!apiKey) {
            return { statusCode: 400, headers, body: JSON.stringify({ error: 'Missing x-api-key header', message: 'Missing x-api-key header' }) };
        }

        const response = await fetch('https://api.anthropic.com/v1/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': apiKey,
                'anthropic-version': anthropicVersion
            },
            body: JSON.stringify(rawBody)
        });

        const data = await response.json();

        return {
            statusCode: response.status,
            headers: { ...headers, 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        };

    } catch (error) {
        return {
            statusCode: 500,
            headers: { ...headers, 'Content-Type': 'application/json' },
            body: JSON.stringify({ error: 'Internal proxy error', message: error.message })
        };
    }
};
