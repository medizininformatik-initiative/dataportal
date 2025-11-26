import { withMermaid } from "vitepress-plugin-mermaid";

export default withMermaid({
    title: 'Dataportal',
    description: 'Dataportal Documentation',
    ignoreDeadLinks: true,
    base: process.env.DOCS_BASE || '',
    appearance: true,
    lastUpdated: true,
    themeConfig: {
        siteTitle: false,

        editLink: {
            pattern: 'https://github.com/medizininformatik-initiative/dataportal/edit/main/docs/:path',
            text: 'Edit this page on GitHub'
        },

        socialLinks: [
            { icon: 'github', link: 'https://github.com/medizininformatik-initiative/dataportal' }
        ],

        footer: {
            message: 'Released under the <a href="https://www.apache.org/licenses/LICENSE-2.0">Apache License 2.0</a>',
        },

        search: {
            provider: 'local'
        },

        outline: {
            level: [2, 3]
        },

        nav: [
            { text: 'Home', link: '/' }
        ],

        sidebar: [
            {
                text: 'Home',
                link: '/index.md',
                activeMatch: '^/$'
            },
            {
                text: 'Overview',
                link: '/overview.md',
                activeMatch: '^/$'
            },
            {
                text: 'Architecture',
                link: '/architecture.md',
                activeMatch: '^/$'
            },
            {
                text: 'Data Portal',
                link: '/data-portal/overview.md',
                items: [
                    { text: 'Overview', link: '/data-portal/overview.md' },
                ]
            },
            {
                text: 'Data Node',
                link: '/data-node/overview.md',
                items: [
                    { text: 'Overview', link: '/data-node/overview.md' },
                    { text: 'Architecture', link: '/data-node/architecture.md' },
                    { text: 'DUP Pipeline', link: '/data-node/dup-pipeline.md' },
                    {
                        text: 'Use',
                        link: '/data-node/use.md',
                        items: [
                            { text: 'fhir-data-evaluator', link: '/data-node/fhir-data-evaluator.md' },
                            { text: 'aether', link: '/data-node/aether.md' }
                        ]
                    },
                ]
            }
        ]
    }
})