import metaData from "~/data/meta";
const { titleSuffix } = metaData;

export function themeGeneratorTitle(colorName) {
  return `Minimal ${colorName} theme ${titleSuffix}`;
}
export function themeGeneratorDescription(colorName) {
  return `CSS code to customize femto's primary color to ${colorName} with CSS variables.`;
}
