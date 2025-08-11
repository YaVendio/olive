# Guía de Contribución / Contributing Guide

[English version below](#english-version)

## Versión en Español

¡Gracias por tu interés en contribuir a Olive! Este documento proporciona las pautas para contribuir al proyecto.

### Código de Conducta

Este proyecto se adhiere a un código de conducta. Al participar, se espera que respetes este código.

### Cómo Contribuir

1. **Fork el repositorio**
   ```bash
   git clone git@github.com:tu-usuario/olive.git
   cd olive
   ```

2. **Crea una rama para tu feature**
   ```bash
   git checkout -b feature/nueva-caracteristica
   ```

3. **Instala las dependencias de desarrollo**
   ```bash
   uv sync --all-extras --dev
   ```

4. **Realiza tus cambios**
   - Sigue el estilo de código PEP 8
   - Agrega tests para nuevas funcionalidades
   - Actualiza la documentación si es necesario

5. **Ejecuta los tests**
   ```bash
   uv run pytest
   uv run ruff check .
   uv run basedpyright
   ```

6. **Commit tus cambios**
   ```bash
   git commit -m "feat: agrega nueva característica X"
   ```
   Usamos [Conventional Commits](https://www.conventionalcommits.org/)

7. **Push y crea un Pull Request**
   ```bash
   git push origin feature/nueva-caracteristica
   ```

### Tipos de Contribuciones

- **Reportar bugs**: Usa GitHub Issues
- **Sugerir características**: Abre una discusión primero
- **Mejorar documentación**: Siempre bienvenido
- **Agregar tests**: Ayuda a mejorar la cobertura
- **Corregir bugs**: Revisa los issues abiertos

### Estándares de Código

- Python 3.13+
- Formato con `ruff`
- Type hints obligatorios
- Docstrings en español o inglés
- Tests para nueva funcionalidad

---

## English Version

Thank you for your interest in contributing to Olive! This document provides guidelines for contributing to the project.

### Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

### How to Contribute

1. **Fork the repository**
   ```bash
   git clone git@github.com:your-username/olive.git
   cd olive
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```

3. **Install development dependencies**
   ```bash
   uv sync --all-extras --dev
   ```

4. **Make your changes**
   - Follow PEP 8 style guide
   - Add tests for new features
   - Update documentation as needed

5. **Run the tests**
   ```bash
   uv run pytest
   uv run ruff check .
   uv run basedpyright
   ```

6. **Commit your changes**
   ```bash
   git commit -m "feat: add new feature X"
   ```
   We use [Conventional Commits](https://www.conventionalcommits.org/)

7. **Push and create a Pull Request**
   ```bash
   git push origin feature/new-feature
   ```

### Types of Contributions

- **Bug reports**: Use GitHub Issues
- **Feature suggestions**: Open a discussion first
- **Documentation improvements**: Always welcome
- **Test additions**: Help improve coverage
- **Bug fixes**: Check open issues

### Code Standards

- Python 3.13+
- Format with `ruff`
- Type hints required
- Docstrings in Spanish or English
- Tests for new functionality
