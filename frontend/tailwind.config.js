/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      "colors": {
        "surface-container-low": "#f7f3f2",
        "on-secondary": "#ffffff",
        "on-secondary-fixed-variant": "#454747",
        "on-tertiary-fixed-variant": "#484645",
        "secondary-fixed-dim": "#c6c6c7",
        "surface-container-lowest": "#ffffff",
        "tertiary": "#000000",
        "outline": "#747878",
        "surface-container": "#f1edec",
        "tertiary-container": "#1c1b1a",
        "surface-tint": "#5f5e5e",
        "primary-fixed": "#e5e2e1",
        "on-primary-container": "#858383",
        "on-secondary-fixed": "#1a1c1c",
        "inverse-surface": "#313030",
        "tertiary-fixed-dim": "#cac6c4",
        "on-background": "#1c1b1b",
        "on-primary-fixed": "#1c1b1b",
        "outline-variant": "#c4c7c7",
        "on-error": "#ffffff",
        "inverse-on-surface": "#f4f0ef",
        "error": "#ba1a1a",
        "primary": "#000000",
        "on-primary-fixed-variant": "#474646",
        "on-secondary-container": "#5f6161",
        "on-surface": "#1c1b1b",
        "surface-container-high": "#ebe7e6",
        "error-container": "#ffdad6",
        "primary-container": "#1c1b1b",
        "surface-dim": "#ddd9d8",
        "primary-fixed-dim": "#c8c6c5",
        "surface": "#fdf8f8",
        "on-primary": "#ffffff",
        "secondary": "#5d5f5f",
        "secondary-fixed": "#e2e2e2",
        "surface-container-highest": "#e5e2e1",
        "on-error-container": "#93000a",
        "on-surface-variant": "#444748",
        "secondary-container": "#dcdddd",
        "surface-bright": "#fdf8f8",
        "on-tertiary-container": "#868381",
        "background": "#fdf8f8",
        "surface-variant": "#e5e2e1",
        "on-tertiary": "#ffffff",
        "inverse-primary": "#c8c6c5",
        "on-tertiary-fixed": "#1c1b1a",
        "tertiary-fixed": "#e6e1df"
      },
      "borderRadius": {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px"
      },
      "spacing": {
        "xl": "64px",
        "border_width": "1.5px",
        "base": "4px",
        "gutter": "24px",
        "md": "24px",
        "lg": "40px",
        "sm": "16px",
        "xs": "8px"
      },
      "fontFamily": {
        "code": ["Space Grotesk"],
        "h1": ["Space Grotesk"],
        "label-caps": ["Space Grotesk"],
        "body": ["Inter"],
        "h2": ["Space Grotesk"],
        "mono-body": ["Space Grotesk"]
      },
      "fontSize": {
        "code": ["16px", { "lineHeight": "1.7", "fontWeight": "500" }],
        "h1": ["36px", { "lineHeight": "1.1", "letterSpacing": "-0.02em", "fontWeight": "800" }],
        "label-caps": ["14px", { "lineHeight": "1", "letterSpacing": "0.05em", "fontWeight": "800" }],
        "body": ["16px", { "lineHeight": "1.6", "letterSpacing": "0", "fontWeight": "500" }],
        "h2": ["28px", { "lineHeight": "1.2", "letterSpacing": "-0.01em", "fontWeight": "700" }],
        "mono-body": ["15px", { "lineHeight": "1.5", "letterSpacing": "0", "fontWeight": "500" }]
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries')
  ],
}

